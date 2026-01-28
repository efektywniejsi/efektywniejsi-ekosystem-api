"""Pydantic schemas for sales page sections."""

from typing import Any, Literal

from pydantic import BaseModel, Field

SectionType = Literal[
    "hero",
    "features",
    "testimonials",
    "faq",
    "pricing",
    "countdown",
    "video",
    "cta",
    "stats",
    "curriculum",
    "instructor",
    "guarantee",
    "gallery",
    "rich_text",
    "custom_html",
]


# --- Individual section config schemas ---


class HeroConfig(BaseModel):
    headline: str = ""
    subheadline: str = ""
    cta_text: str = ""
    cta_url: str = ""
    background_image_url: str = ""
    overlay_opacity: float = Field(default=0.5, ge=0, le=1)


class FeatureItem(BaseModel):
    icon: str = ""
    title: str = ""
    description: str = ""


class FeaturesConfig(BaseModel):
    title: str = ""
    subtitle: str = ""
    columns: int = Field(default=3, ge=1, le=4)
    items: list[FeatureItem] = Field(default_factory=list, max_length=20)


class TestimonialItem(BaseModel):
    quote: str = ""
    author: str = ""
    title: str = ""
    image_url: str = ""
    rating: int = Field(default=5, ge=1, le=5)


class TestimonialsConfig(BaseModel):
    title: str = ""
    items: list[TestimonialItem] = Field(default_factory=list, max_length=20)


class FaqItem(BaseModel):
    question: str = ""
    answer: str = ""


class FaqConfig(BaseModel):
    title: str = ""
    items: list[FaqItem] = Field(default_factory=list, max_length=20)


class PricingFeature(BaseModel):
    text: str = ""
    included: bool = True


class PricingCard(BaseModel):
    title: str = ""
    price: str = ""
    period: str = ""
    features: list[PricingFeature] = Field(default_factory=list, max_length=20)
    cta_text: str = ""
    cta_url: str = ""
    badge: str = ""
    highlighted: bool = False


class PricingConfig(BaseModel):
    title: str = ""
    subtitle: str = ""
    cards: list[PricingCard] = Field(default_factory=list, max_length=5)


class CountdownConfig(BaseModel):
    title: str = ""
    target_date: str = ""
    expired_text: str = ""


class VideoConfig(BaseModel):
    title: str = ""
    video_url: str = ""
    mux_playback_id: str = ""
    caption: str = ""


class CtaConfig(BaseModel):
    headline: str = ""
    description: str = ""
    button_text: str = ""
    button_url: str = ""
    variant: Literal["primary", "secondary", "gradient"] = "primary"


class StatItem(BaseModel):
    value: str = ""
    label: str = ""
    icon: str = ""


class StatsConfig(BaseModel):
    title: str = ""
    items: list[StatItem] = Field(default_factory=list, max_length=20)


class CurriculumConfig(BaseModel):
    title: str = ""
    show_lesson_count: bool = True
    show_duration: bool = True


class SocialLink(BaseModel):
    platform: str = ""
    url: str = ""


class InstructorConfig(BaseModel):
    name: str = ""
    title: str = ""
    bio: str = ""
    image_url: str = ""
    social_links: list[SocialLink] = Field(default_factory=list, max_length=10)


class GuaranteeConfig(BaseModel):
    title: str = ""
    description: str = ""
    icon: str = ""
    days: int = Field(default=14, ge=0)


class GalleryImage(BaseModel):
    url: str = ""
    alt: str = ""
    caption: str = ""


class GalleryConfig(BaseModel):
    title: str = ""
    images: list[GalleryImage] = Field(default_factory=list, max_length=20)
    columns: int = Field(default=3, ge=1, le=4)


class RichTextConfig(BaseModel):
    content: Any = None  # TipTap JSON document


class CustomHtmlConfig(BaseModel):
    html: str = ""
    css: str = ""


# --- Section type to config mapping ---

SECTION_CONFIG_MAP: dict[str, type[BaseModel]] = {
    "hero": HeroConfig,
    "features": FeaturesConfig,
    "testimonials": TestimonialsConfig,
    "faq": FaqConfig,
    "pricing": PricingConfig,
    "countdown": CountdownConfig,
    "video": VideoConfig,
    "cta": CtaConfig,
    "stats": StatsConfig,
    "curriculum": CurriculumConfig,
    "instructor": InstructorConfig,
    "guarantee": GuaranteeConfig,
    "gallery": GalleryConfig,
    "rich_text": RichTextConfig,
    "custom_html": CustomHtmlConfig,
}


# --- Section wrapper ---


class SalesPageSection(BaseModel):
    id: str
    type: SectionType
    sort_order: int = 0
    visible: bool = True
    config: dict = Field(default_factory=dict)


class SalesPageSettings(BaseModel):
    theme: Literal["dark", "light"] = "dark"
    custom_css: str = ""


class SalesPageData(BaseModel):
    version: int = 1
    sections: list[SalesPageSection] = Field(default_factory=list, max_length=30)
    settings: SalesPageSettings = Field(default_factory=SalesPageSettings)


class SalesPageResponse(BaseModel):
    sales_page_sections: SalesPageData | None = None


class SalesPageUpdateRequest(BaseModel):
    sales_page_sections: SalesPageData
