"""API Key 用例单元测试 - 账号 hello / 密码 12345678"""
import hashlib
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta

from src.application.use_cases.api_key.create_api_key import (
    CreateApiKeyCommand,
    CreateApiKeyResult,
    CreateApiKeyUseCase,
)
from src.application.use_cases.api_key.revoke_api_key import (
    RevokeApiKeyCommand,
    RevokeApiKeyUseCase,
)
from src.domain.api_key.aggregate import ApiKey
from src.domain.api_key.value_objects import ApiKeyStatus
from src.domain.shared.value_objects import TokenId, UserId, Timestamp
from src.domain.shared.exceptions import TokenNotFoundException


# ---------------------------------------------------------------------------
# 共用夹具
# ---------------------------------------------------------------------------

USER_ID = "00000000-0000-0000-0000-000000000001"
USERNAME = "hello"
PASSWORD = "12345678"  # 仅用于标注测试场景，不参与 API Key 逻辑


def _make_api_key(name: str = "test-key", revoked: bool = False) -> ApiKey:
    """构造一个 ApiKey 聚合根（不经过数据库）"""
    plain = "plaintext_key_abc123"
    key_hash = hashlib.sha256(plain.encode()).hexdigest()
    user_id = UserId.from_string(USER_ID)
    api_key = ApiKey.create(
        user_id=user_id,
        name=name,
        key_hash=key_hash,
        plain_key=plain,
    )
    if revoked:
        api_key.revoke()
    return api_key


# ---------------------------------------------------------------------------
# CreateApiKeyUseCase 测试
# ---------------------------------------------------------------------------

class TestCreateApiKeyUseCase:
    """测试创建 API Key 用例（用户 hello）"""

    @pytest.fixture
    def mock_repo(self):
        repo = AsyncMock()
        repo.save = AsyncMock(return_value=None)
        return repo

    @pytest.fixture
    def use_case(self, mock_repo):
        return CreateApiKeyUseCase(api_key_repository=mock_repo)

    @pytest.mark.asyncio
    async def test_create_api_key_success(self, use_case, mock_repo):
        """正常创建 API Key，返回明文 key 且仅返回一次"""
        command = CreateApiKeyCommand(user_id=USER_ID, name="my-key")
        result: CreateApiKeyResult = await use_case.execute(command)

        assert result.api_key_id is not None
        assert result.name == "my-key"
        assert result.plain_key is not None and len(result.plain_key) > 0
        assert result.expires_at is None
        mock_repo.save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_api_key_with_expiry(self, use_case, mock_repo):
        """带过期时间创建 API Key"""
        expires = datetime.utcnow() + timedelta(days=30)
        command = CreateApiKeyCommand(
            user_id=USER_ID, name="expiring-key", expires_at=expires
        )
        result: CreateApiKeyResult = await use_case.execute(command)

        assert result.expires_at == expires
        mock_repo.save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_api_key_plain_key_is_hashed_before_save(self, use_case, mock_repo):
        """保存时存储的是哈希值，而非明文"""
        command = CreateApiKeyCommand(user_id=USER_ID, name="hash-check-key")
        result = await use_case.execute(command)

        saved_api_key: ApiKey = mock_repo.save.call_args[0][0]
        expected_hash = hashlib.sha256(result.plain_key.encode()).hexdigest()
        assert saved_api_key.key_hash == expected_hash

    @pytest.mark.asyncio
    async def test_create_api_key_empty_name_raises(self, use_case):
        """名称为空时应抛出异常"""
        command = CreateApiKeyCommand(user_id=USER_ID, name="   ")
        with pytest.raises(Exception):
            await use_case.execute(command)


# ---------------------------------------------------------------------------
# RevokeApiKeyUseCase 测试
# ---------------------------------------------------------------------------

class TestRevokeApiKeyUseCase:
    """测试撤销 API Key 用例（用户 hello）"""

    @pytest.fixture
    def existing_api_key(self):
        return _make_api_key(name="to-revoke")

    @pytest.fixture
    def mock_repo(self, existing_api_key):
        repo = AsyncMock()
        repo.find_by_id = AsyncMock(return_value=existing_api_key)
        repo.save = AsyncMock(return_value=None)
        return repo

    @pytest.fixture
    def use_case(self, mock_repo):
        return RevokeApiKeyUseCase(api_key_repository=mock_repo)

    @pytest.mark.asyncio
    async def test_revoke_api_key_success(self, use_case, mock_repo, existing_api_key):
        """正常撤销 API Key"""
        command = RevokeApiKeyCommand(
            api_key_id=str(existing_api_key.id),
            user_id=USER_ID,
        )
        await use_case.execute(command)

        assert existing_api_key.status == ApiKeyStatus.REVOKED
        mock_repo.save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_revoke_api_key_not_found_raises(self, use_case, mock_repo):
        """API Key 不存在时抛出 TokenNotFoundException"""
        mock_repo.find_by_id = AsyncMock(return_value=None)
        command = RevokeApiKeyCommand(
            api_key_id="00000000-0000-0000-0000-999999999999",
            user_id=USER_ID,
        )
        with pytest.raises(TokenNotFoundException):
            await use_case.execute(command)

    @pytest.mark.asyncio
    async def test_revoke_api_key_wrong_owner_raises(self, use_case, mock_repo):
        """用户只能撤销自己的 API Key，操作他人的应抛出异常"""
        other_user_id = "00000000-0000-0000-0000-000000000099"
        command = RevokeApiKeyCommand(
            api_key_id=str((await mock_repo.find_by_id(None)).id),
            user_id=other_user_id,
        )
        with pytest.raises(TokenNotFoundException):
            await use_case.execute(command)

    @pytest.mark.asyncio
    async def test_revoke_already_revoked_is_idempotent(self, use_case, mock_repo, existing_api_key):
        """重复撤销应幂等，不抛出异常"""
        existing_api_key.revoke()  # 预先撤销
        command = RevokeApiKeyCommand(
            api_key_id=str(existing_api_key.id),
            user_id=USER_ID,
        )
        await use_case.execute(command)  # 不应抛出
        assert existing_api_key.status == ApiKeyStatus.REVOKED


# ---------------------------------------------------------------------------
# ApiKey 聚合根领域逻辑测试
# ---------------------------------------------------------------------------

class TestApiKeyAggregate:
    """测试 ApiKey 聚合根的领域规则"""

    def test_new_api_key_is_active(self):
        api_key = _make_api_key()
        assert api_key.status == ApiKeyStatus.ACTIVE
        assert api_key.is_valid() is True

    def test_revoked_api_key_is_invalid(self):
        api_key = _make_api_key(revoked=True)
        assert api_key.status == ApiKeyStatus.REVOKED
        assert api_key.is_valid() is False

    def test_expired_api_key_is_invalid(self):
        plain = "key"
        key_hash = hashlib.sha256(plain.encode()).hexdigest()
        user_id = UserId.from_string(USER_ID)
        api_key = ApiKey.create(
            user_id=user_id,
            name="expired",
            key_hash=key_hash,
            plain_key=plain,
            expires_at=datetime(2000, 1, 1),  # 过去的时间
        )
        assert api_key.is_valid() is False

    def test_plain_key_accessible_after_create(self):
        api_key = _make_api_key()
        assert api_key.plain_key == "plaintext_key_abc123"

    def test_domain_event_published_on_create(self):
        from src.domain.api_key.events import ApiKeyCreated
        api_key = _make_api_key()
        events = api_key.events
        assert any(isinstance(e, ApiKeyCreated) for e in events)

    def test_domain_event_published_on_revoke(self):
        from src.domain.api_key.events import ApiKeyRevoked
        api_key = _make_api_key()
        api_key.revoke()
        events = api_key.events
        assert any(isinstance(e, ApiKeyRevoked) for e in events)
