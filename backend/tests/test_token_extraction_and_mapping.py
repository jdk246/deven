from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db import Base
from app.models import Token, TokenMention, TokenSnapshot
from app.services.token_extraction import TokenExtractionService
from app.services.token_mapping import TokenMappingService


def _make_in_memory_session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    return SessionLocal()


def _add_token(
    db: Session,
    *,
    chain_id: str,
    contract_address: str,
    symbol: str,
    liquidity: float | None = None,
    volume_24h: float | None = None,
) -> None:
    db.add(
        Token(
            chain_id=chain_id,
            contract_address=contract_address,
            symbol=symbol,
            name=f"{symbol} Token",
            decimals=18,
        )
    )
    if liquidity is not None or volume_24h is not None:
        db.add(
            TokenSnapshot(
                chain_id=chain_id,
                contract_address=contract_address,
                liquidity=liquidity,
                volume_24h=volume_24h,
            )
        )
    db.flush()


def test_extracts_evm_contract_address() -> None:
    service = TokenExtractionService(_make_in_memory_session())
    mentions = service.extract_mentions(
        "Watch 0x4200000000000000000000000000000000000006 if attention keeps building."
    )

    assert len(mentions) == 1
    assert mentions[0].mention_type == "contract_address"
    assert mentions[0].contract_address == "0x4200000000000000000000000000000000000006"


def test_rejects_invalid_evm_address() -> None:
    service = TokenExtractionService(_make_in_memory_session())
    mentions = service.extract_mentions("This string 0x1234 should not be treated as a token address.")

    assert mentions == []


def test_extracts_single_cashtag() -> None:
    service = TokenExtractionService(_make_in_memory_session())
    mentions = service.extract_mentions("Keeping an eye on $BNB today.")

    assert len(mentions) == 1
    assert mentions[0].mention_type == "cashtag"
    assert mentions[0].symbol_text == "BNB"


def test_extracts_multiple_cashtags() -> None:
    service = TokenExtractionService(_make_in_memory_session())
    mentions = service.extract_mentions("$BNB still leads, but $SOL and $WIF are moving too.")

    symbols = [mention.symbol_text for mention in mentions if mention.mention_type == "cashtag"]
    assert symbols == ["BNB", "SOL", "WIF"]


def test_no_mentions_returns_empty_list() -> None:
    service = TokenExtractionService(_make_in_memory_session())
    assert service.extract_mentions("No token references here, just general commentary.") == []


def test_exact_contract_mapping_resolves_to_known_token() -> None:
    db = _make_in_memory_session()
    try:
        _add_token(
            db,
            chain_id="56",
            contract_address="0x1111111111111111111111111111111111111111",
            symbol="TRACE",
        )
        mention = TokenMention(
            post_id=1,
            mention_type="contract_address",
            chain_id=None,
            contract_address="0x1111111111111111111111111111111111111111",
            is_resolved=False,
        )

        mapped = TokenMappingService(db).map_mention(mention)

        assert mapped.is_resolved is True
        assert mapped.chain_id == "56"
        assert mapped.contract_address == "0x1111111111111111111111111111111111111111"
        assert mapped.confidence == 1.0
    finally:
        db.close()


def test_cashtag_mapping_resolves_to_existing_local_token() -> None:
    db = _make_in_memory_session()
    try:
        _add_token(
            db,
            chain_id="56",
            contract_address="0x2222222222222222222222222222222222222222",
            symbol="BNB",
        )
        mention = TokenMention(
            post_id=1,
            mention_type="cashtag",
            symbol_text="BNB",
            is_resolved=False,
        )

        mapped = TokenMappingService(db).map_mention(mention)

        assert mapped.is_resolved is True
        assert mapped.chain_id == "56"
        assert mapped.contract_address == "0x2222222222222222222222222222222222222222"
        assert mapped.symbol_text == "BNB"
    finally:
        db.close()


def test_duplicate_symbol_without_market_data_stays_unresolved() -> None:
    db = _make_in_memory_session()
    try:
        _add_token(
            db,
            chain_id="56",
            contract_address="0x3333333333333333333333333333333333333333",
            symbol="PEPE",
        )
        _add_token(
            db,
            chain_id="8453",
            contract_address="0x4444444444444444444444444444444444444444",
            symbol="PEPE",
        )
        mention = TokenMention(
            post_id=1,
            mention_type="cashtag",
            symbol_text="PEPE",
            is_resolved=False,
        )

        mapped = TokenMappingService(db).map_mention(mention)

        assert mapped.is_resolved is False
        assert mapped.chain_id is None
        assert mapped.contract_address is None
        assert mapped.symbol_text == "PEPE"
    finally:
        db.close()


def test_duplicate_symbol_resolves_by_higher_liquidity() -> None:
    db = _make_in_memory_session()
    try:
        _add_token(
            db,
            chain_id="56",
            contract_address="0x5555555555555555555555555555555555555555",
            symbol="ALPHA",
            liquidity=150_000.0,
            volume_24h=500_000.0,
        )
        _add_token(
            db,
            chain_id="8453",
            contract_address="0x6666666666666666666666666666666666666666",
            symbol="ALPHA",
            liquidity=900_000.0,
            volume_24h=100_000.0,
        )
        mention = TokenMention(
            post_id=1,
            mention_type="cashtag",
            symbol_text="ALPHA",
            is_resolved=False,
        )

        mapped = TokenMappingService(db).map_mention(mention)

        assert mapped.is_resolved is True
        assert mapped.chain_id == "8453"
        assert mapped.contract_address == "0x6666666666666666666666666666666666666666"
    finally:
        db.close()


def test_duplicate_symbol_resolves_by_higher_volume_when_liquidity_is_missing() -> None:
    db = _make_in_memory_session()
    try:
        _add_token(
            db,
            chain_id="56",
            contract_address="0x7777777777777777777777777777777777777777",
            symbol="BETA",
            liquidity=None,
            volume_24h=90_000.0,
        )
        _add_token(
            db,
            chain_id="CT_501",
            contract_address="So11111111111111111111111111111111111111112",
            symbol="BETA",
            liquidity=None,
            volume_24h=210_000.0,
        )
        mention = TokenMention(
            post_id=1,
            mention_type="cashtag",
            symbol_text="BETA",
            is_resolved=False,
        )

        mapped = TokenMappingService(db).map_mention(mention)

        assert mapped.is_resolved is True
        assert mapped.chain_id == "CT_501"
        assert mapped.contract_address == "So11111111111111111111111111111111111111112"
    finally:
        db.close()
