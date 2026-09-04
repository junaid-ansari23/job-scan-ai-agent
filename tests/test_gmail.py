from typing import Any
from unittest.mock import MagicMock

import pytest

from app.tools.gmail import GmailEmailReader


def _request(response: dict[str, Any]) -> MagicMock:
    request = MagicMock()
    request.execute.return_value = response
    return request


def test_gmail_reader_paginates_and_fetches_full_messages() -> None:
    service = MagicMock()
    messages_resource = service.users.return_value.messages.return_value
    messages_resource.list.side_effect = [
        _request({"messages": [{"id": "m1"}], "nextPageToken": "next"}),
        _request({"messages": [{"id": "m2"}]}),
    ]
    messages_resource.get.side_effect = [
        _request({"id": "m1", "payload": {"headers": []}}),
        _request({"id": "m2", "payload": {"headers": []}}),
    ]

    messages = GmailEmailReader(service).get_recent_emails(24)

    assert [message.message_id for message in messages] == ["m1", "m2"]
    assert messages_resource.list.call_count == 2
    messages_resource.get.assert_any_call(userId="me", id="m1", format="full")
    messages_resource.get.assert_any_call(userId="me", id="m2", format="full")
    assert messages_resource.list.call_args_list[0].kwargs["q"].startswith("after:")


def test_gmail_reader_rejects_invalid_lookback() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        GmailEmailReader(MagicMock()).get_recent_emails(0)
