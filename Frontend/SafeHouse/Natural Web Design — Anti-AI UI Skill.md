# Natural Web Design — Anti-AI UI Skill

## Purpose

Design and refine websites so they feel **intentional, human-designed, distinctive, and visually grounded** rather than like generic AI-generated interfaces.

The goal is not to make websites imperfect.

The goal is to make them feel like a **real designer made deliberate decisions**.

Before considering a design finished, ask:

> **Could this website have been generated from a generic “modern SaaS landing page” prompt?**

If yes, redesign it.

---

# 1. Core Design Philosophy

Every design decision must have a reason.

Do not add visual elements simply because there is empty space.

Do not add animations simply because animations are possible.

Do not turn every piece of content into a card.

Do not use trends as decoration.

Instead:

- Establish a clear visual identity.
- Create hierarchy.
- Use contrast intentionally.
- Allow some asymmetry.
- Use whitespace where it improves readability.
- Use density where information benefits from density.
- Make components feel native to the product.
- Make the interface reflect the subject matter.

The website should feel like it belongs to its specific product.

---

# 2. Avoid Generic AI Design Patterns

Avoid these unless the product genuinely requires them:

### Excessive glassmorphism

Do not automatically use:

- `backdrop-filter: blur()`
- translucent cards
- glowing borders
- frosted panels
- floating glass containers

Glass should never become the default visual language.

### Excessive rounded corners

Do not make every element:

```css
border-radius: 24px;
```

Use different radii intentionally.

Possible hierarchy:

- buttons: 6–10px
- small controls: 4–8px
- panels: 8–16px
- large containers: only when visually justified

Sharp or lightly rounded geometry can often feel more sophisticated.

### Gradient addiction

Avoid:

- purple → blue gradients
- pink → purple gradients
- blue → cyan gradients
- glowing gradient text
- gradient borders everywhere

A gradient should communicate something meaningful.

### Generic floating cards

Avoid building every section as:

```text
┌──────────────────────┐
│      ICON            │
│                      │
│  Heading             │
│  Description         │
│                      │
│  Learn More →        │
└──────────────────────┘
```

Repeated card structures quickly make a website look AI-generated.

---

# 3. Color

Use a **small, intentional palette**.

Prefer:

- 1 dominant background
- 1 primary text color
- 1 secondary text color
- 1 primary accent
- optional secondary accent

Colors should come from the product's identity.

Do not automatically use:

- neon purple
- electric blue
- cyberpunk gradients
- black + purple + cyan
- glowing white text

### Environmental products

For products related to:

- energy
- climate
- agriculture
- sustainability
- outdoors
- physical infrastructure

consider colors inspired by the real environment.

For example:

```text
Sky
Grass
Soil
Sunlight
Metal
Concrete
Wood
Water
```

The palette should feel connected to the physical world.

---

# 4. Typography

Typography should feel editorial and deliberate.

Use a limited type system.

Recommended hierarchy:

```text
Display
Large heading
Section heading
Body
Small label
Metadata
```

Do not randomly use 8–12 font sizes.

Avoid:

- enormous headings everywhere
- excessive bold text
- uppercase text everywhere
- excessive letter spacing
- tiny unreadable labels

Use typography to establish hierarchy rather than decorative effects.

---

# 5. Layout

Do not make every section symmetrical.

Use controlled asymmetry.

Examples:

```text
Image        Text
     Text
            Image
```

or:

```text
        Main statement

Supporting information
                 Visual
```

or:

```text
Large visual

          Small technical detail

Secondary content
```

The composition should have rhythm.

Avoid:

```text
Card Card Card
Card Card Card
Card Card Card
```

unless a grid genuinely makes sense.

---

# 6. Visual Rhythm

A good page should breathe.

Alternate between:

- dense areas
- quiet areas
- visual moments
- informational moments

Do not give every section identical padding.

Avoid:

```text
py-24
py-24
py-24
py-24
py-24
```

Instead, determine spacing based on content hierarchy.

Some sections may need:

```text
64px
```

others:

```text
96px
```

and major transitions:

```text
140px+
```

Spacing should create rhythm rather than mathematical uniformity.

---

# 7. Components

Components should reflect their purpose.

Do not create a universal component and force everything into it.

Bad:

```text
Everything = Card
Everything = Badge
Everything = Pill
Everything = Floating Panel
```

Better:

- technical information → technical panel
- statistics → compact metric
- navigation → navigation system
- narrative → editorial layout
- comparison → structured comparison
- controls → physical-looking controls when appropriate
- warnings → visual warning treatment

Each component should communicate what it represents.

---

# 8. Real-World References

When designing a website, think about the physical world associated with the product.

For example, a solar-energy website could draw inspiration from:

- engineering manuals
- solar farms
- weather stations
- industrial control panels
- architectural magazines
- field equipment
- environmental dashboards
- scientific diagrams
- outdoor signage

Do not automatically make it look like a futuristic AI company.

If the product exists in the physical world, let the interface reflect that world.

---

# 9. Animation

Animation should have a purpose.

Good animation:

- communicates state
- shows cause and effect
- guides attention
- creates continuity
- explains physical behavior
- reinforces the product's identity

Bad animation:

- everything fades in
- everything floats
- everything scales on hover
- infinite particle backgrounds
- random blobs
- excessive parallax
- constant glowing

### Animation principle

Ask:

> **What is this animation communicating?**

If the answer is “it looks cool,” remove it or simplify it.

---

# 10. Physicality

When appropriate, give interfaces a sense of physical existence.

Use:

- subtle shadows
- realistic depth
- material-inspired surfaces
- restrained borders
- environmental textures
- mechanical movement
- believable lighting

But avoid fake 3D decoration.

For example, a solar tracker should behave like a physical solar tracker.

Its:

- panel
- motor
- azimuth
- tilt
- sunlight
- shadow
- environment

should visually relate to one another.

---

# 11. Natural Interaction

Interactions should feel predictable.

Hover states should not dramatically transform elements.

Prefer:

```text
small movement
small color shift
small elevation change
subtle emphasis
```

rather than:

```text
huge scale
glow explosion
rotation
blur
particle burst
```

Interaction should feel like touching a well-designed physical object.

---

# 12. Avoid AI-Generated Copy

Never use generic marketing phrases unless they genuinely belong to the brand.

Avoid phrases such as:

- “Unlock your potential”
- “Revolutionize your workflow”
- “The future of…”
- “Seamless experience”
- “Powered by cutting-edge AI”
- “Transform the way you…”
- “Next-generation solution”
- “Empowering businesses”
- “Built for the future”

Prefer concrete language.

Instead of:

> Revolutionizing solar energy management.

Use:

> Track how each panel moves with the sun.

Instead of:

> Unlock powerful insights.

Use:

> See which panels are producing less than expected.

Specific beats impressive.

---

# 13. Product-Specific Identity

Before designing, identify:

### What is this product?

### Who uses it?

### Where does it exist?

### What does it feel like physically?

### What visual language naturally belongs to it?

### What would a human designer reference when designing it?

Use those answers to determine:

- color
- typography
- spacing
- imagery
- animation
- component shapes
- interaction patterns

Never begin with:

> “Make it modern.”

Begin with:

> “What should this product feel like?”

---

# 14. Visual Authenticity Test

Before finishing, inspect the entire website and look for:

### AI-Slop Indicators

- [ ] Too many rounded cards
- [ ] Too many gradients
- [ ] Excessive glassmorphism
- [ ] Generic purple/blue palette
- [ ] Every section has the same structure
- [ ] Every element has a shadow
- [ ] Too many badges
- [ ] Too many pills
- [ ] Excessive floating elements
- [ ] Generic SaaS copy
- [ ] Excessive whitespace with no purpose
- [ ] Huge meaningless hero heading
- [ ] Decorative animations everywhere
- [ ] Generic stock-style imagery
- [ ] Repetitive card grids
- [ ] Every section looks interchangeable

If several are present, redesign.

---

# 15. Human Designer Test

Ask:

### Test 1 — Identity

Could I remove the logo and still identify what product this is?

If no → strengthen the visual identity.

### Test 2 — Specificity

Could this design be reused for:

```text
AI startup
Crypto startup
Fintech startup
Productivity app
Solar company
```

without changing much?

If yes → it is too generic.

### Test 3 — Restraint

Is every visual effect necessary?

If no → remove some.

### Test 4 — Memory

Does the website have one or two visual moments people will remember?

If no → create one.

### Test 5 — Physical World

If this product exists in reality, does the website feel connected to that reality?

If no → ground the design.

---

# 16. Code Quality

The visual design should not come at the expense of maintainability.

Keep:

- reusable components
- semantic HTML
- accessible interactions
- responsive layouts
- consistent design tokens
- meaningful class names
- clean component boundaries

Do not duplicate large blocks of markup simply to create visual variation.

Use design tokens for:

```css
--background
--foreground
--muted
--accent
--border
--radius
--spacing
```

But allow intentional exceptions when they improve the composition.

---

# 17. Responsive Design

Do not treat mobile as:

```text
Desktop
↓
Stack everything
```

Instead redesign the composition for the smaller screen.

Ask:

- What deserves to remain visible?
- What can disappear?
- What should become scrollable?
- What should become condensed?
- Which visual should remain dominant?
- Does the interaction still make sense?

Mobile should feel designed, not collapsed.

---

# 18. Design Review Before Completion

Before declaring the implementation finished:

1. Open the actual website.
2. Inspect the complete page.
3. Look at desktop.
4. Look at tablet.
5. Look at mobile.
6. Check animation.
7. Check hover states.
8. Check typography.
9. Check spacing.
10. Check color balance.
11. Check whether sections feel repetitive.
12. Remove unnecessary visual effects.
13. Replace generic copy.
14. Add product-specific details.
15. Ask whether the design feels human.

Do not rely only on code inspection.

**Look at the rendered website.**

---

# 19. Final Rule

The objective is not:

> “Make the website look less AI.”

The objective is:

> **Make the website look like someone cared about it.**

Every visual decision should feel intentional.

Every animation should have a reason.

Every color should belong.

Every component should serve a purpose.

Every section should contribute to the identity.

And when something looks impressive but unnecessary:

**remove it.**

A restrained, specific, memorable interface is better than a visually overloaded one.\
\
20\. Human-Written Copy — Anti-AI Language

The website's text must feel like it was written by a **real person who understands the product**, not generated by an AI writing assistant.

Visual authenticity is not enough.

A human-looking website with AI-sounding copy still feels AI-generated.

---

## Core Principle

Write like a knowledgeable human explaining something clearly.

Do not try to sound:

- impressive
- corporate
- inspirational
- futuristic
- sophisticated
- overly polished

Prefer:

- specific
- direct
- natural
- conversational
- concrete
- slightly imperfect when appropriate
- confident without exaggeration

The copy should sound like someone actually **uses and understands the product**.

---

# 21. Ban Generic AI Phrases

Avoid phrases commonly associated with AI-generated marketing copy.

### Avoid:

```text
Unlock the power of...
Unlock new possibilities...
Revolutionize...
Transform the way...
Take your experience to the next level...
Seamlessly...
Cutting-edge...
Next-generation...
State-of-the-art...
Harness the power of...
Empower...
Elevate...
Redefine...
Reimagine...
Unleash...
Game-changing...
Groundbreaking...
Innovative solution...
Comprehensive solution...
Robust platform...
Powerful ecosystem...
Intelligent insights...
Actionable insights...
Meaningful insights...
Drive efficiency...
Drive growth...
Optimize your workflow...
Streamline your operations...
Built for the future...
The future of...
Where innovation meets...
Designed to empower...
Built to transform...

```

These phrases should trigger an automatic rewrite.

---

# 22. Avoid AI Sentence Patterns

AI-generated copy often follows predictable structures.

Avoid:

> “X is more than just Y. It is Z.”

Example:

> SolarGrid is more than just a monitoring platform. It is the future of intelligent solar management.

Rewrite it.

---

Avoid:

> “Whether you're X, Y, or Z, [product] helps you…”

Example:

> Whether you're a homeowner, installer, or energy manager, SolarGrid helps you...

This structure is heavily overused.

---

Avoid:

> “From X to Y, [product]…”

Example:

> From monitoring performance to optimizing energy production, SolarGrid...

Rewrite it using actual product capabilities.

---

Avoid:

> “With X, you can…”

when repeated throughout the page.

---

Avoid excessive:

> “Designed to…”

> “Built to…”

> “Made to…”

> “Created to…”

---

# 23. Prefer Concrete Language

Bad:

> Gain powerful insights into your solar infrastructure.

Better:

> See which panels are producing less than they should.

Bad:

> Optimize your solar energy performance.

Better:

> Find panels that are losing output and see why.

Bad:

> Harness the power of intelligent tracking.

Better:

> The tracker follows the sun throughout the day.

Bad:

> Experience smarter solar management.

Better:

> Check today's production, panel angle, and tracker status in one place.

Specific information makes copy feel human.

---

# 24. Write Like a Product Team

Imagine the copy was written by:

- the founder
- the engineer
- the product designer
- the person who actually operates the system

Not by a marketing copy generator.

Use language that a real product team would put into the interface.

For example:

```text
Tracker position
23.4°

Today's production
48.2 kWh

Panel temperature
37°C

Last movement
12:42 PM

```

This feels more believable than:

```text
Intelligent Solar Insights
Unlock unprecedented visibility into your renewable energy ecosystem.

```

---

# 25. Headlines

Headlines should be short and meaningful.

Prefer:

> Follow the sun.

> Know what your panels are doing.

> See your solar system clearly.

> Every panel has a story.

> Track the movement. Track the output.

> Your panels, in motion.

Avoid giant generic headlines such as:

> Revolutionizing the Future of Intelligent Solar Energy Management

The headline should communicate an idea, not demonstrate vocabulary.

---

# 26. Subheadings

A subheading should explain the headline.

Bad:

> Smarter technology for a brighter tomorrow.

Better:

> Track panel movement, production, and system health from one dashboard.

Bad:

> Intelligence that works for you.

Better:

> See where production drops and which panels need attention.

---

# 27. Buttons

Buttons should describe the action.

Prefer:

```text
View dashboard
See how it works
Check production
Explore the system
View tracker
Get started

```

Avoid:

```text
Unlock Now
Discover More
Learn More → 
Explore the Future
Start Your Journey
Experience Innovation

```

Especially avoid using **“Learn More” everywhere**.

---

# 28. Microcopy

Microcopy should sound natural.

Bad:

> Please enter the required information to continue your seamless experience.

Better:

> Enter your location to calculate today's sun position.

Bad:

> No data available at this time.

Better:

> Nothing here yet.

Bad:

> Successfully completed.

Better:

> Saved.

Bad:

> An error has occurred while processing your request.

Better:

> Something went wrong. Try again.

Use the shortest natural sentence that communicates the meaning.

---

# 29. Don't Over-Explain

AI tends to explain simple things three times.

If a heading already communicates the idea, don't repeat it immediately in the paragraph.

Bad:

> ## Track every panel

> Track every panel in your solar installation with our powerful tracking system. Our platform lets you monitor every panel so you can keep track of your panels.

Better:

> ## Track every panel

> See panel position, output, and movement in real time.

---

# 30. Avoid Perfectly Structured Copy

Human writing doesn't always follow:

```text
Problem
↓
Solution
↓
Benefit
↓
Call to action

```

on every section.

Allow sections to have different rhythms.

For example:

```text
A small label

THE SUN MOVES.
YOUR PANELS SHOULD TOO.

A short explanation.

[Visual]

```

Then another section might simply be:

```text
48.2 kWh

Today's production.

```

Variation makes the page feel designed rather than generated from a template.

---

# 31. Use Real Details

Whenever possible, replace generic claims with actual details.

Instead of:

> Powerful solar tracking technology.

Use:

> Dual-axis tracking keeps the panel facing the strongest available sunlight.

Instead of:

> Real-time monitoring.

Use:

> Production updates every 30 seconds.

Instead of:

> Advanced analytics.

Use:

> Compare today's output with the last seven days.

Real details create credibility.

---

# 32. Don't Fake Specificity

Never invent:

- statistics
- customer numbers
- performance improvements
- technical specifications
- testimonials
- company history
- certifications
- awards

If the information isn't available, don't manufacture it just to make the website sound convincing.

Use neutral copy instead.

---

# 33. Natural Imperfection

Human copy does not need to be perfectly symmetrical.

Do not force every section into the same grammatical structure.

For example:

```text
01
Find the angle.

02
Follow the sun.

03
See what changed.

```

is perfectly acceptable.

So is:

```text
One dashboard.
Less guessing.

```

Short fragments can be more natural than polished corporate sentences.

---

# 34. Avoid Excessive Adjectives

AI often stacks adjectives:

> A powerful, intelligent, innovative, seamless, next-generation solar platform.

Delete almost all of them.

Prefer:

> A dashboard for tracking solar panels.

Let the product demonstrate its quality.

---

# 35. Human Tone Test

Before finishing, read every sentence aloud.

Ask:

> **Would a normal person actually say this?**

If the answer is no, rewrite it.

Then ask:

> **Would a company employee actually write this on their website?**

If the answer is no, rewrite it.

Then ask:

> **Does this sentence say something specific?**

If not, delete it.

---

# 36. The "AI Detector" Test

Do not attempt to bypass AI detectors.

Instead, use this as a **writing-quality test**.

Look for:

- repetitive sentence structures
- excessive adjectives
- corporate buzzwords
- vague claims
- unnatural enthusiasm
- unnecessary metaphors
- overly formal language
- repeated concepts
- predictable three-part lists
- identical paragraph lengths
- unnecessary transition phrases

Rewrite until the copy sounds like a real product team wrote it.

---

# 37. Final Copy Rule

The goal is NOT:

> “Make AI writing undetectable.”

The goal is:

> **Make the writing worth reading.**

The reader should feel:

> “Someone who understands this product wrote this.”

Not:

> “Someone prompted an AI to write a landing page.”

When choosing between:

**impressive wording**

and

**clear wording**

always choose clear wording.

When choosing between:

**generic marketing**

and

**specific information**

always choose specific information.

When choosing between:

**perfectly polished**

and

**natural**

choose natural.

---

# 38. Final Website Copy Review

Before completing the website:

- Remove generic marketing phrases.
- Remove unnecessary adjectives.
- Replace vague claims with concrete information.
- Shorten long sentences.
- Remove repeated ideas.
- Replace generic button labels.
- Check headings for specificity.
- Check every paragraph for unnecessary explanation.
- Read the copy aloud.
- Make sure the copy sounds like the product team wrote it.
- Make sure the copy actually describes the product.
- Remove anything that exists only to sound impressive.

### Final question:

> **If I removed the design and showed someone only the text, would they still believe a real person wrote it?**

If not, rewrite it.

---

## Final Self-Critique

Before finishing, answer these questions internally:

```text
1. What makes this website visually unique?

2. What part would a generic AI generator probably get wrong?

3. Are there too many cards?

4. Are there too many rounded corners?

5. Are there unnecessary gradients?

6. Does the color palette belong to the product?

7. Does the typography feel intentional?

8. Does the animation communicate anything?

9. Does the layout have rhythm?

10. Does the website feel connected to the real world?

11. Could I mistake this for a generic AI-generated website?

If yes:
REDESIGN.
```

**Design with intention.**\
**Remove decoration without purpose.**\
**Make the interface belong to its product.**
