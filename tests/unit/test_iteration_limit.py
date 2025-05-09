import asyncio

import pytest

from openhands.controller.agent_controller import AgentController
from openhands.core.schema import AgentState
from openhands.events import EventStream
from openhands.events.action import MessageAction
from openhands.events.event import EventSource
from openhands.llm.metrics import Metrics


class DummyAgent:
    def __init__(self):
        self.name = 'dummy'
        self.llm = type(
            'DummyLLM',
            (),
            {
                'metrics': Metrics(),
                'config': type('DummyConfig', (), {'max_message_chars': 10000})(),
            },
        )()

    def reset(self):
        pass

    def get_system_message(self):
        # Return a proper SystemMessageAction for the refactored system message handling
        from openhands.events.action.message import SystemMessageAction
        from openhands.events.event import EventSource

        system_message = SystemMessageAction(content='This is a dummy system message')
        system_message._source = EventSource.AGENT
        system_message._id = -1  # Set invalid ID to avoid the ID check
        return system_message


@pytest.mark.asyncio
async def test_iteration_limit_extends_on_user_message():
    # Initialize test components
    from openhands.storage.memory import InMemoryFileStore

    file_store = InMemoryFileStore()
    event_stream = EventStream(sid='test', file_store=file_store)
    agent = DummyAgent()
    initial_max_iterations = 100
    controller = AgentController(
        agent=agent,
        event_stream=event_stream,
        max_iterations=initial_max_iterations,
        sid='test',
        headless_mode=False,
    )

    # Set initial state
    await controller.set_agent_state_to(AgentState.RUNNING)
    controller.state.iteration = 90  # Close to the limit
    assert controller.state.max_iterations == initial_max_iterations

    # Simulate user message
    user_message = MessageAction('test message', EventSource.USER)
    event_stream.add_event(user_message, EventSource.USER)
    await asyncio.sleep(0.1)  # Give time for event to be processed

    # Verify max_iterations was extended
    assert controller.state.max_iterations == 90 + initial_max_iterations

    # Simulate more iterations and another user message
    controller.state.iteration = 180  # Close to new limit
    user_message2 = MessageAction('another message', EventSource.USER)
    event_stream.add_event(user_message2, EventSource.USER)
    await asyncio.sleep(0.1)  # Give time for event to be processed

    # Verify max_iterations was extended again
    assert controller.state.max_iterations == 180 + initial_max_iterations
