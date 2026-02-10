"""System prompts for Claude AI post generation."""

from pathlib import Path


def load_brand_voice() -> str:
    """Load the brand voice guidelines from markdown file."""
    brand_voice_path = Path(__file__).parent.parent / "config" / "brand_voice.md"
    try:
        return brand_voice_path.read_text()
    except FileNotFoundError:
        return ""


SYSTEM_PROMPT = """You are a social media content creator for San Diego Custom Painting (SDCP), a family-owned painting contractor serving San Diego since 1998.

{brand_voice}

## Your Task

You will receive project photos and context from the painting crew. Your job is to create engaging social media captions that:

1. Showcase the quality craftsmanship visible in the photos
2. Match SDCP's professional, confident brand voice
3. Connect with San Diego homeowners looking for painting services
4. Drive engagement and inquiries

## Important Rules

- ONLY describe what you can actually see in the photos
- NEVER make up details about the project that aren't provided
- Focus on transformation, craftsmanship, and customer value
- Use approved vocabulary and phrases from the brand guide
- Avoid words like "perfect," "flawless," "guarantee"
- End with an appropriate call-to-action
"""


INSTAGRAM_CAPTION_PROMPT = """Create an Instagram caption for this painting project.

**Project Context:**
{context}

**Requirements:**
- Under 150 words (punchy and concise)
- Start with a strong hook that grabs attention
- Focus on the transformation or craftsmanship visible
- Write 2-4 sentences maximum
- End with a clear call-to-action
- DO NOT include any hashtags in the caption (they will be added separately)
- Professional but engaging tone

**Caption Structure:**
1. Hook (attention-grabbing opening)
2. Value statement (what makes this special)
3. CTA (call-to-action)

Return ONLY the caption text, nothing else."""


FACEBOOK_CAPTION_PROMPT = """Create a Facebook caption for this painting project.

**Project Context:**
{context}

**Requirements:**
- Slightly longer and more conversational than Instagram
- Can include more context/story about the project
- Still professional but warmer, more community-focused
- 3-5 sentences
- End with a call-to-action
- DO NOT include any hashtags
- Focus on the homeowner experience and transformation

**Caption Structure:**
1. Opening that connects with homeowners
2. Details about the work (what you see in the photos)
3. Value/benefit to the homeowner
4. CTA

Return ONLY the caption text, nothing else."""


HASHTAG_PROMPT = """Select appropriate hashtags for this painting project post.

**Project Context:**
{context}

**Hashtag Library (select from these):**

Core SDCP Hashtags (always include 3-5):
#SanDiegoCustomPainting, #SDCustomPainting, #SanDiegoPainter, #SanDiegoPainters, #PaintersSanDiego, #SDPainting, #HomePainterSanDiego

San Diego Location Tags (include 2-3 based on project location):
#SanDiegoHomes, #SanDiegoHomeImprovement, #SanDiegoDesigner, #LaJollaHomes, #DelMarHomes, #EncinitasHomes, #RanchoSantaFe, #CarlsbadHomes, #SanDiegoRealEstate

Service-Specific (include 2-4 based on what's shown):
#InteriorPaintingSD, #ExteriorPaintingSD, #InteriorDesigner, #HomeImprovementSD, #CabinetPainting, #ExteriorPainting, #InteriorPainting

Transformation Tags (include 1-2 if before/after):
#BeforeAndAfter, #HomeTransformation, #PaintingTransformation, #HomeMakeover

General Home/Design (include 3-5):
#HomeImprovement, #HouseGoals, #HomeRenovation, #PaintingContractor, #ProfessionalPainter, #HomeDesign, #InteriorDesign, #CurbAppeal

**Requirements:**
- Select 15-20 total hashtags
- Mix of branded, location, service, and general tags
- If location is mentioned, include relevant location hashtags
- Match hashtags to what's actually shown in the project

Return ONLY a JSON array of hashtag strings, like:
["#SanDiegoCustomPainting", "#InteriorPaintingSD", ...]"""


PHOTO_ANALYSIS_PROMPT = """Analyze this painting project photo and describe what you see.

Focus on:
1. Type of space (interior/exterior, room type)
2. Paint colors visible
3. Quality indicators (clean lines, even coverage, prep work)
4. Before/after if applicable
5. Any notable features or challenges

Keep the description factual and concise (2-3 sentences).
This will be used to help generate social media captions."""


def get_system_prompt() -> str:
    """Get the full system prompt with brand voice loaded."""
    brand_voice = load_brand_voice()
    return SYSTEM_PROMPT.format(brand_voice=brand_voice)


def get_instagram_prompt(context: str) -> str:
    """Get Instagram caption prompt with context."""
    return INSTAGRAM_CAPTION_PROMPT.format(context=context)


def get_facebook_prompt(context: str) -> str:
    """Get Facebook caption prompt with context."""
    return FACEBOOK_CAPTION_PROMPT.format(context=context)


def get_hashtag_prompt(context: str) -> str:
    """Get hashtag selection prompt with context."""
    return HASHTAG_PROMPT.format(context=context)
