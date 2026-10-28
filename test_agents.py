"""Real LangGraph integration with a local scripted model, without API calls."""
import importlib.util
import unittest

HAS_DEPS = importlib.util.find_spec('langgraph') is not None


@unittest.skipUnless(HAS_DEPS, 'Install requirements.txt to test LangGraph integration')
class GraphTests(unittest.TestCase):
    def test_specialists_use_tools_and_review_revises_plan(self):
        from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
        from langchain_core.messages import AIMessage
        from langchain_core.runnables import RunnableLambda
        from agents import build_graph

        class ScriptedModel(FakeMessagesListChatModel):
            proposals: int = 0

            def bind_tools(self, tools, **kwargs):
                return self

            def with_structured_output(self, schema, **kwargs):
                def propose(_):
                    self.proposals += 1
                    return schema(tenant_filter=True, current_only=True,
                                  timeout_ms=100 if self.proposals == 1 else 300,
                                  retries=0 if self.proposals == 1 else 1)
                return RunnableLambda(propose)

        messages = []
        for i in range(2):
            messages.extend([AIMessage(content='', tool_calls=[{
                'name': 'inspect_cases', 'args': {}, 'id': f'inspect-{i}'}]),
                AIMessage(content='Evidence inspected: fix filters, timeout and retries.')])
        model = ScriptedModel(responses=messages)
        result = build_graph(model).invoke({'brief': 'Investigate the synthetic customer incidents.'})
        self.assertEqual(result['rounds'], 2)
        self.assertEqual(result['status'], 'sandbox_approved')
        self.assertEqual(sum(s.get('tool_calls', 0) for s in result['trace']), 2)
