"""Single-run application orchestration."""

from collections.abc import Callable

from chaoxing_stalker.chaoxing.client import ChaoXingClient
from chaoxing_stalker.config import DEFAULT_CONFIG_PATH, load_config, validate_config
from chaoxing_stalker.notifiers.factory import create_notifiers
from chaoxing_stalker.services.assignment_check import AssignmentProviderFactory, check_and_notify


def run_once(
    config: dict,
    assignment_provider_factory: AssignmentProviderFactory = ChaoXingClient,
    notifier_factory: Callable = create_notifiers,
) -> None:
    """Check every configured user once without persisting assignment state."""
    for user in config["users"]:
        _process_user(
            user,
            assignment_provider_factory,
            notifier_factory,
        )


def run_from_config(config_path: str = DEFAULT_CONFIG_PATH) -> None:
    config = load_config(config_path)
    validate_config(config)
    run_once(config)


def _process_user(
    user: dict,
    assignment_provider_factory: AssignmentProviderFactory,
    notifier_factory: Callable,
) -> None:
    username = user.get("chaoxing", {}).get("username", "?")
    try:
        notifiers = notifier_factory(user)
        check_and_notify(
            user,
            notifiers,
            assignment_provider_factory,
        )
    except Exception as error:
        print(f"[ERROR] [{username}] 处理失败: {error}")
