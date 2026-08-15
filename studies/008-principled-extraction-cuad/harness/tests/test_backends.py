import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from harness.backends.base import Backend, BackendError, BackendUnavailable
from harness.backends.ollama_backend import OllamaBackend
from harness.backends.tinker_backend import TINKER_MODEL_FACTS, TinkerBackend

MODEL_MAX = 32768


class _Handler(BaseHTTPRequestHandler):
    behavior: dict = {}

    def log_message(self, *args):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length) or b"{}")
        if self.path == "/api/show":
            body = {
                "model_info": {"qwen3.5.context_length": self.behavior.get("model_max", MODEL_MAX)},
                "parameters": self.behavior.get("parameters", "num_ctx 8192\nstop \"<|im_end|>\""),
            }
        elif self.path.endswith("/chat/completions"):
            body = {
                "choices": [
                    {
                        "index": 0,
                        "message": {"content": '{"ok": true}', "reasoning_content": "hm"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 4},
                "echo_payload": payload,
            }
        elif self.path == "/api/chat":
            body = {
                "message": {"content": self.behavior.get("content", '{"ok": true}')},
                "prompt_eval_count": self.behavior.get("prompt_eval_count", 1000000),
                "eval_count": 12,
                "done_reason": "stop",
                "echo_options": payload.get("options"),
                "echo_format": payload.get("format"),
            }
        else:
            self.send_response(404)
            self.end_headers()
            return
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture
def server():
    _Handler.behavior = {}
    httpd = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_port}", _Handler
    httpd.shutdown()


def test_ollama_reads_the_real_context_window_from_the_server(server):
    host, handler = server
    backend = OllamaBackend(model="qwen3.5:8b", num_ctx=8192, host=host)
    assert backend.model_max_context == MODEL_MAX
    assert backend.modelfile_num_ctx == 8192
    assert backend.context_limit == 8192
    assert backend.notes["model_max_context"] == MODEL_MAX


def test_ollama_refuses_a_num_ctx_beyond_the_trained_window(server):
    host, handler = server
    with pytest.raises(BackendError) as exc:
        OllamaBackend(model="qwen3.5:8b", num_ctx=MODEL_MAX * 2, host=host)
    assert "silently truncate" in str(exc.value)


def test_ollama_fails_loudly_when_the_context_length_is_unknown(server):
    host, handler = server
    handler.behavior = {"model_max": None}
    with pytest.raises(BackendError) as exc:
        OllamaBackend(model="qwen3.5:8b", num_ctx=4096, host=host)
    assert "refusing to guess" in str(exc.value)


def test_ollama_detects_silent_prompt_truncation(server):
    host, handler = server
    backend = OllamaBackend(model="qwen3.5:8b", num_ctx=8192, host=host)
    handler.behavior = {"prompt_eval_count": 5}
    with pytest.raises(BackendError) as exc:
        backend.sample(
            messages=[{"role": "user", "content": "x" * 40000}],
            json_schema=None,
            temperature=0.0,
            seed=0,
            max_tokens=16,
        )
    assert "silently truncated" in str(exc.value)


def test_ollama_passes_num_ctx_seed_and_schema_through(server):
    host, handler = server
    backend = OllamaBackend(model="qwen3.5:8b", num_ctx=8192, host=host)
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}}
    result = backend.sample(
        messages=[{"role": "user", "content": "hi"}],
        json_schema=schema,
        temperature=0.3,
        seed=7,
        max_tokens=16,
    )
    options = result.raw["echo_options"]
    assert options == {"num_ctx": 8192, "temperature": 0.3, "seed": 7, "num_predict": 16}
    assert result.raw["echo_format"] == schema
    assert result.n_completion_tokens == 12


def test_ollama_unreachable_raises_backend_unavailable():
    with pytest.raises(BackendUnavailable):
        OllamaBackend(model="m", num_ctx=1024, host="http://127.0.0.1:1")


def test_tinker_requires_a_key(monkeypatch):
    monkeypatch.delenv("TINKER_API_KEY", raising=False)
    with pytest.raises(BackendUnavailable):
        TinkerBackend()


def test_tinker_declares_prompt_plus_parse_structured_output(monkeypatch):
    monkeypatch.setenv("TINKER_API_KEY", "dummy")
    backend = TinkerBackend()
    assert backend.structured_output == "prompt_only"
    assert backend.advertised_context_limit == 262144
    assert backend.context_limit == 262144 - backend.safety_margin
    assert backend.describe()["model"] == "thinkingmachines/Inkling-Small"


@pytest.mark.parametrize(
    "model,advertised,mechanism",
    [
        ("Qwen/Qwen3.5-4B", 65536, "prompt_only"),
        ("Qwen/Qwen3.5-9B", 65536, "prompt_only"),
        ("thinkingmachines/Inkling-Small", 262144, "prompt_only"),
    ],
)
def test_measured_context_and_structured_output_are_declared_per_model(
    monkeypatch, model, advertised, mechanism
):
    monkeypatch.setenv("TINKER_API_KEY", "dummy")
    backend = TinkerBackend(model=model)
    assert backend.advertised_context_limit == advertised
    assert backend.structured_output == mechanism
    assert backend.context_limit < advertised
    assert backend.notes["context_measurement"]


def test_context_limit_is_below_advertised_so_the_boundary_is_never_ridden(monkeypatch):
    monkeypatch.setenv("TINKER_API_KEY", "dummy")
    nine_b = TinkerBackend(model="Qwen/Qwen3.5-9B")
    assert nine_b.context_limit <= 65530
    assert nine_b.safety_margin > TinkerBackend(model="Qwen/Qwen3.5-4B").safety_margin


def test_an_unmeasured_model_is_refused_rather_than_guessed(monkeypatch):
    monkeypatch.setenv("TINKER_API_KEY", "dummy")
    with pytest.raises(BackendError) as exc:
        TinkerBackend(model="Qwen/Qwen9.9-999B")
    assert "rather than guessing" in str(exc.value)
    assert TinkerBackend(model="Qwen/Qwen9.9-999B", context_limit=4096).context_limit < 4096


def test_canonical_model_ids_are_substrate_neutral():
    from harness.model_registry import served_name

    assert served_name("Qwen/Qwen3.5-9B", "tinker") == "Qwen/Qwen3.5-9B"
    assert served_name("Qwen/Qwen3.5-9B", "ollama") == "qwen3.5:9b"
    assert served_name("Qwen/Qwen3.5-4B", "ollama") == "qwen3.5:4b"


def test_the_model_id_recorded_in_results_is_the_canonical_one(monkeypatch):
    monkeypatch.setenv("TINKER_API_KEY", "dummy")
    backend = TinkerBackend(model="Qwen/Qwen3.5-9B")
    assert backend.model_id == "Qwen/Qwen3.5-9B"
    assert backend.served_model == "Qwen/Qwen3.5-9B"


def test_backend_interface_is_all_a_new_backend_must_implement():
    required = {
        name
        for name, member in vars(Backend).items()
        if getattr(member, "__isabstractmethod__", False)
    }
    assert required == {"sample"}
    for backend_cls in (OllamaBackend, TinkerBackend):
        assert backend_cls.structured_output in ("json_schema", "json_object", "prompt_only")
        assert hasattr(backend_cls, "count_tokens")


def test_heuristic_token_count_is_declared_not_assumed(monkeypatch):
    monkeypatch.setenv("TINKER_API_KEY", "dummy")
    backend = TinkerBackend()
    assert backend.token_count_method == "heuristic"
    assert backend.count_tokens("a" * 400) == 100


def test_requesting_a_tokenizer_without_transformers_fails_loudly(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "transformers":
            raise ImportError("no transformers")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setenv("TINKER_API_KEY", "dummy")
    with pytest.raises(BackendError) as exc:
        TinkerBackend(tokenizer_id="Qwen/Qwen3-8B")
    assert "refusing to fall back" in str(exc.value)


def test_exact_token_counting_is_used_when_a_tokenizer_is_present(monkeypatch):
    monkeypatch.setenv("TINKER_API_KEY", "dummy")
    backend = TinkerBackend()

    class StubTokenizer:
        def encode(self, text, add_special_tokens=False):
            return text.split()

    backend._tokenizer = StubTokenizer()
    backend.token_count_method = "exact"
    assert backend.count_tokens("a b c d e") == 5


def test_no_tinker_model_claims_enforced_structured_output(monkeypatch):
    monkeypatch.setenv("TINKER_API_KEY", "dummy")
    for model in TINKER_MODEL_FACTS:
        backend = TinkerBackend(model=model)
        assert backend.structured_output == "prompt_only"
        assert "NOT enforced" in backend.notes["structured_output_enforcement"]


def test_response_format_is_never_sent(monkeypatch, server):
    host, handler = server
    monkeypatch.setenv("TINKER_API_KEY", "dummy")
    backend = TinkerBackend(model="Qwen/Qwen3.5-4B", base_url=host + "/oai")
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}}
    result = backend.sample(
        messages=[{"role": "user", "content": "hi"}],
        json_schema=schema,
        temperature=0.3,
        seed=7,
        max_tokens=16,
    )
    sent = result.raw["echo_payload"]
    assert "response_format" not in sent
    assert "guided_json" not in sent
    assert "structured_outputs" not in sent
    assert result.request_params is not None
    assert "response_format" not in result.request_params


def test_separate_reasoning_is_sent_explicitly(monkeypatch, server):
    host, handler = server
    monkeypatch.setenv("TINKER_API_KEY", "dummy")
    backend = TinkerBackend(model="Qwen/Qwen3.5-4B", base_url=host + "/oai")
    result = backend.sample(
        messages=[{"role": "user", "content": "hi"}],
        json_schema=None,
        temperature=0.0,
        seed=0,
        max_tokens=8,
    )
    sent = result.raw["echo_payload"]
    assert "separate_reasoning" in sent
    assert sent["separate_reasoning"] is True
    assert result.request_params["separate_reasoning"] is True
    assert backend.describe()["separate_reasoning"] is True


def test_separate_reasoning_is_not_left_to_the_server_default(monkeypatch):
    monkeypatch.setenv("TINKER_API_KEY", "dummy")
    backend = TinkerBackend(model="Qwen/Qwen3.5-4B", separate_reasoning=False)
    assert backend.separate_reasoning is False
    assert backend.notes["separate_reasoning"] is False
    assert "flipped from" in backend.notes["separate_reasoning_note"]


def test_tinker_declares_that_seeds_are_not_honored(monkeypatch):
    monkeypatch.setenv("TINKER_API_KEY", "dummy")
    backend = TinkerBackend(model="Qwen/Qwen3.5-9B")
    assert backend.seed_honored is False
    assert backend.describe()["seed_honored"] is False
    assert "repetition LABEL" in backend.notes["seed_note"]


def test_ollama_reports_seeds_as_honored(server):
    host, handler = server
    backend = OllamaBackend(model="qwen3.5:9b", num_ctx=8192, host=host)
    assert backend.seed_honored is True
    assert backend.describe()["seed_honored"] is True
