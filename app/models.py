from sqlmodel import SQLModel, Field, Relationship, JSON, Column
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from decimal import Decimal


class ScrapeStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    BLOCKED = "blocked"  # For anti-scraping measures


class AntiScrapingMeasure(str, Enum):
    NONE = "none"
    CLOUDFLARE = "cloudflare"
    CAPTCHA = "captcha"
    RATE_LIMIT = "rate_limit"
    USER_AGENT_BLOCK = "user_agent_block"
    IP_BLOCK = "ip_block"
    OTHER = "other"


# Persistent models (stored in database)
class LotteryWebsite(SQLModel, table=True):
    """Stores information about lottery websites to scrape"""

    __tablename__ = "lottery_websites"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, description="Display name of the lottery")
    url: str = Field(max_length=500, unique=True, description="Base URL of the website")
    country: str = Field(max_length=50, description="Country where lottery operates")
    is_active: bool = Field(default=True, description="Whether to scrape this website")
    scrape_interval_minutes: int = Field(default=60, description="How often to scrape in minutes")
    last_scraped_at: Optional[datetime] = Field(default=None, description="Last successful scrape timestamp")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Scraping configuration
    selectors: Dict[str, str] = Field(
        default={}, sa_column=Column(JSON), description="CSS selectors for data extraction"
    )
    headers: Dict[str, str] = Field(default={}, sa_column=Column(JSON), description="Custom HTTP headers")
    anti_scraping_config: Dict[str, Any] = Field(
        default={}, sa_column=Column(JSON), description="Config for handling anti-scraping"
    )

    # Relationships
    scrape_sessions: List["ScrapeSession"] = Relationship(back_populates="website")
    lottery_draws: List["LotteryDraw"] = Relationship(back_populates="website")


class ScrapeSession(SQLModel, table=True):
    """Records each scraping attempt and its results"""

    __tablename__ = "scrape_sessions"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    website_id: int = Field(foreign_key="lottery_websites.id")
    status: ScrapeStatus = Field(default=ScrapeStatus.PENDING)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)
    duration_seconds: Optional[Decimal] = Field(default=None, decimal_places=3)

    # Anti-scraping details
    anti_scraping_detected: AntiScrapingMeasure = Field(default=AntiScrapingMeasure.NONE)
    bypass_method_used: Optional[str] = Field(default=None, max_length=100)
    user_agent: Optional[str] = Field(default=None, max_length=500)
    ip_address: Optional[str] = Field(default=None, max_length=45)

    # Results
    draws_found: int = Field(default=0, description="Number of lottery draws found")
    draws_new: int = Field(default=0, description="Number of new draws added")
    error_message: Optional[str] = Field(default=None, max_length=1000)
    response_status_code: Optional[int] = Field(default=None)
    response_headers: Dict[str, str] = Field(default={}, sa_column=Column(JSON))

    # Relationships
    website: LotteryWebsite = Relationship(back_populates="scrape_sessions")


class LotteryDraw(SQLModel, table=True):
    """Stores individual lottery draw results"""

    __tablename__ = "lottery_draws"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    website_id: int = Field(foreign_key="lottery_websites.id")

    # Draw identification
    draw_date: datetime = Field(description="Date of the lottery draw")
    draw_number: Optional[str] = Field(default=None, max_length=50, description="Official draw number if available")
    game_name: Optional[str] = Field(default=None, max_length=100, description="Name of the specific game")

    # Winning numbers
    winning_numbers: List[int] = Field(sa_column=Column(JSON), description="Main winning numbers")
    bonus_numbers: List[int] = Field(default=[], sa_column=Column(JSON), description="Bonus/supplementary numbers")
    special_numbers: Dict[str, Any] = Field(
        default={}, sa_column=Column(JSON), description="Other special numbers or info"
    )

    # Additional lottery information
    jackpot_amount: Optional[Decimal] = Field(default=None, decimal_places=2, description="Jackpot prize amount")
    currency: Optional[str] = Field(default=None, max_length=3, description="Currency code (USD, HKD, AUD, etc.)")
    winners_count: Optional[int] = Field(default=None, description="Number of jackpot winners")
    next_draw_date: Optional[datetime] = Field(default=None, description="Date of next draw")

    # Prize breakdown
    prize_breakdown: List[Dict[str, Any]] = Field(
        default=[], sa_column=Column(JSON), description="Prize tiers and amounts"
    )

    # Metadata
    raw_data: Dict[str, Any] = Field(default={}, sa_column=Column(JSON), description="Raw scraped data for debugging")
    scraped_at: datetime = Field(default_factory=datetime.utcnow, description="When this draw was scraped")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    website: LotteryWebsite = Relationship(back_populates="lottery_draws")


# Non-persistent schemas (for validation, forms, API requests/responses)
class LotteryWebsiteCreate(SQLModel, table=False):
    name: str = Field(max_length=100)
    url: str = Field(max_length=500)
    country: str = Field(max_length=50)
    is_active: bool = Field(default=True)
    scrape_interval_minutes: int = Field(default=60, ge=1, le=1440)  # 1 minute to 24 hours
    selectors: Dict[str, str] = Field(default={})
    headers: Dict[str, str] = Field(default={})
    anti_scraping_config: Dict[str, Any] = Field(default={})


class LotteryWebsiteUpdate(SQLModel, table=False):
    name: Optional[str] = Field(default=None, max_length=100)
    url: Optional[str] = Field(default=None, max_length=500)
    country: Optional[str] = Field(default=None, max_length=50)
    is_active: Optional[bool] = Field(default=None)
    scrape_interval_minutes: Optional[int] = Field(default=None, ge=1, le=1440)
    selectors: Optional[Dict[str, str]] = Field(default=None)
    headers: Optional[Dict[str, str]] = Field(default=None)
    anti_scraping_config: Optional[Dict[str, Any]] = Field(default=None)


class ScrapeSessionCreate(SQLModel, table=False):
    website_id: int
    user_agent: Optional[str] = Field(default=None, max_length=500)
    ip_address: Optional[str] = Field(default=None, max_length=45)


class ScrapeSessionUpdate(SQLModel, table=False):
    status: Optional[ScrapeStatus] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    duration_seconds: Optional[Decimal] = Field(default=None, decimal_places=3)
    anti_scraping_detected: Optional[AntiScrapingMeasure] = Field(default=None)
    bypass_method_used: Optional[str] = Field(default=None, max_length=100)
    draws_found: Optional[int] = Field(default=None, ge=0)
    draws_new: Optional[int] = Field(default=None, ge=0)
    error_message: Optional[str] = Field(default=None, max_length=1000)
    response_status_code: Optional[int] = Field(default=None)
    response_headers: Optional[Dict[str, str]] = Field(default=None)


class LotteryDrawCreate(SQLModel, table=False):
    website_id: int
    draw_date: datetime
    draw_number: Optional[str] = Field(default=None, max_length=50)
    game_name: Optional[str] = Field(default=None, max_length=100)
    winning_numbers: List[int]
    bonus_numbers: List[int] = Field(default=[])
    special_numbers: Dict[str, Any] = Field(default={})
    jackpot_amount: Optional[Decimal] = Field(default=None, decimal_places=2)
    currency: Optional[str] = Field(default=None, max_length=3)
    winners_count: Optional[int] = Field(default=None, ge=0)
    next_draw_date: Optional[datetime] = Field(default=None)
    prize_breakdown: List[Dict[str, Any]] = Field(default=[])
    raw_data: Dict[str, Any] = Field(default={})


class LotteryDrawUpdate(SQLModel, table=False):
    draw_number: Optional[str] = Field(default=None, max_length=50)
    game_name: Optional[str] = Field(default=None, max_length=100)
    winning_numbers: Optional[List[int]] = Field(default=None)
    bonus_numbers: Optional[List[int]] = Field(default=None)
    special_numbers: Optional[Dict[str, Any]] = Field(default=None)
    jackpot_amount: Optional[Decimal] = Field(default=None, decimal_places=2)
    currency: Optional[str] = Field(default=None, max_length=3)
    winners_count: Optional[int] = Field(default=None, ge=0)
    next_draw_date: Optional[datetime] = Field(default=None)
    prize_breakdown: Optional[List[Dict[str, Any]]] = Field(default=None)
    raw_data: Optional[Dict[str, Any]] = Field(default=None)


# Response schemas for API
class LotteryDrawResponse(SQLModel, table=False):
    id: int
    website_id: int
    website_name: str
    draw_date: str  # ISO format string
    draw_number: Optional[str]
    game_name: Optional[str]
    winning_numbers: List[int]
    bonus_numbers: List[int]
    special_numbers: Dict[str, Any]
    jackpot_amount: Optional[Decimal]
    currency: Optional[str]
    winners_count: Optional[int]
    next_draw_date: Optional[str]  # ISO format string
    prize_breakdown: List[Dict[str, Any]]
    scraped_at: str  # ISO format string
    created_at: str  # ISO format string


class ScrapeSessionResponse(SQLModel, table=False):
    id: int
    website_id: int
    website_name: str
    status: ScrapeStatus
    started_at: str  # ISO format string
    completed_at: Optional[str]  # ISO format string
    duration_seconds: Optional[Decimal]
    anti_scraping_detected: AntiScrapingMeasure
    bypass_method_used: Optional[str]
    draws_found: int
    draws_new: int
    error_message: Optional[str]
    response_status_code: Optional[int]


class LotteryWebsiteResponse(SQLModel, table=False):
    id: int
    name: str
    url: str
    country: str
    is_active: bool
    scrape_interval_minutes: int
    last_scraped_at: Optional[str]  # ISO format string
    created_at: str  # ISO format string
    updated_at: str  # ISO format string
    recent_draws_count: Optional[int] = Field(default=None)
    last_scrape_status: Optional[ScrapeStatus] = Field(default=None)
