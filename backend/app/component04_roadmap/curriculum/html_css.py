# Owner: Dewmi - Component 04. Curated lesson bank for HTML and CSS (SK017). Drafted with an AI assistant, checked by the curriculum validator and tests, and reviewed by the C4 author.
SKILL_ID = "SK017"

TOPICS = [
    dict(
        id="html-b1", title="Semantic HTML page structure", stage="Beginner", requires=[],
        objective="Build a page with a doctype, head and body, headings in order, header/nav/main/section/footer, links and images with alt text.",
        main_idea="HTML describes what each part of a page is (a heading, navigation, the main content). Browsers, search engines "
                  "and screen readers use that meaning, so choose elements by meaning, not by how they look.",
        explanation="Every page starts with <!DOCTYPE html>, then <html lang=\"en\"> containing <head> (title, metadata, links to "
                    "CSS) and <body> (what is shown). Inside body, semantic elements describe the parts: <header> for the top "
                    "area, <nav> for the main links, <main> for the content unique to the page (one per page), <section> for a "
                    "themed group with a heading, <article> for a self-contained item such as a blog post, and <footer>. "
                    "Headings go in order: one <h1> for the page title, <h2> for sections, <h3> inside those; never skip levels "
                    "to get a smaller font (that is CSS's job). Links use <a href=\"...\">, and every meaningful <img> needs an "
                    "alt text that says what the image shows (alt=\"\" for purely decorative images). Screen readers let users "
                    "jump between these landmarks and headings, so a page built only from <div>s is much harder to use.",
        foundation=["HTML = meaning (what it is); CSS = looks (how it appears).",
                    "head = information about the page; body = what the visitor sees.",
                    "Before writing a <div>, ask: is there an element that says what this is?"],
        challenge="Rebuild a page made only of <div>s using semantic elements, then open the browser's accessibility tree "
                  "(DevTools > Accessibility) and check that header, nav, main and footer appear as landmarks.",
        example=dict(title="A portfolio page skeleton", language="html",
                     code="<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n  <meta charset=\"utf-8\">\n  <title>Ama Perera - Portfolio</title>\n"
                          "</head>\n<body>\n  <header>\n    <h1>Ama Perera</h1>\n    <nav>\n      <a href=\"#projects\">Projects</a>\n"
                          "      <a href=\"#contact\">Contact</a>\n    </nav>\n  </header>\n  <main>\n    <section id=\"projects\">\n"
                          "      <h2>Projects</h2>\n      <img src=\"weather.png\" alt=\"Weather app showing a 5-day forecast\">\n"
                          "    </section>\n  </main>\n  <footer id=\"contact\">\n    <a href=\"mailto:ama@example.com\">ama@example.com</a>\n"
                          "  </footer>\n</body>\n</html>",
                     steps=["The doctype and <html lang=\"en\"> tell the browser the standard and the language.",
                            "<head> holds the title shown in the browser tab.",
                            "header, nav, main and footer become landmarks that screen reader users can jump between.",
                            "The image has an alt text that describes it, and the headings go h1 then h2."]),
        career_examples=dict(data="A data team's report page uses headings and tables with proper markup, so screen reader users can follow the findings.",
                             software="Front-end developers are asked in code reviews to replace clickable <div>s with real <button>s and <a>s."),
        visual=dict(kind="table", caption="Which element?", columns=["Part of the page", "Element", "Landmark for screen readers"],
                    rows=[["Logo and site title", "<header>", "banner"], ["Main menu links", "<nav>", "navigation"],
                          ["Content unique to this page", "<main>", "main"], ["Copyright and contact", "<footer>", "contentinfo"]],
                    how_to_read="Find the part of your page in the first column; use the element in the second column."),
        key_ideas=["Choose elements by meaning, not by looks.", "One <main> and one <h1> per page; headings in order.",
                   "Every meaningful image needs alt text.", "Landmarks (header, nav, main, footer) help people navigate."],
        mistakes=["Building the whole page from <div>s and <span>s.", "Choosing <h4> because it is small instead of styling with CSS."],
        practice="Write the HTML for a one-page CV: header with your name, nav with two links, main with two sections, and a footer.",
        practical=dict(task="Build a semantic portfolio page (no CSS needed yet) with header, nav, main, at least two sections and a footer.",
                       rubric=["Doctype, lang and a title", "Semantic landmarks and headings in order", "Every image has a meaningful alt text"]),
        next_link="Next you will collect information from users with accessible forms.",
        quiz=[
            dict(id="html-b1-q1", type="single", concept="semantic elements",
                 prompt="Which element should wrap the content that is unique to this page?",
                 options=["<div id=\"main\">", "<main>", "<section>", "<body>"], answer=1,
                 explanation="<main> marks the page's main content and becomes the 'main' landmark. A div has no meaning; body also "
                             "contains the header and footer.",
                 why_wrong={0: "An id does not give a div any meaning for assistive technology.", 3: "body also contains the header, nav and footer."}),
            dict(id="html-b1-q2", type="single", concept="alt text",
                 prompt="What is the alt attribute of an <img> for?",
                 options=["It makes the image load faster", "It describes the image for screen readers and when the image cannot load",
                          "It sets the image size", "It is needed for the image to appear"], answer=1,
                 explanation="alt text replaces the image for people who cannot see it and when the file fails to load."),
            dict(id="html-b1-q3", type="multi", concept="semantic elements",
                 prompt="Which of these elements carry meaning (are semantic)? Select all that apply.",
                 options=["<nav>", "<div>", "<article>", "<span>", "<footer>"], answer=[0, 2, 4],
                 explanation="nav, article and footer say what their content is. div and span are generic containers with no meaning."),
        ],
        diagnostic=[
            dict(id="html-b1-d1", type="single", concept="semantic elements",
                 prompt="Which element is meant for a group of main navigation links?",
                 options=["<nav>", "<links>", "<menu-bar>", "<header>"], answer=0,
                 explanation="<nav> marks a block of navigation links. <links> and <menu-bar> are not HTML elements; header is the top area."),
            dict(id="html-b1-d2", type="single", concept="heading order",
                 prompt="How should you choose between <h2> and <h4>?",
                 options=["By the font size you want", "By the outline: h2 for a section, h3 inside it, h4 inside that",
                          "Always use h4 for small text", "It does not matter"], answer=1,
                 explanation="Headings describe the structure of the content. Size is set with CSS."),
        ],
    ),
    dict(
        id="html-b2", title="Forms and accessible inputs", stage="Beginner", requires=["html-b1"],
        objective="Build forms with labels linked to inputs, the right input types, built-in validation and the right button type.",
        main_idea="A form collects data. Each input needs a label, the right type and simple rules, so every user (also with a "
                  "screen reader or a phone) can fill it in and the browser can catch mistakes early.",
        explanation="<form action=\"/subscribe\" method=\"post\"> sends its fields to the server; each field is sent by its name "
                    "attribute. Link every input to a visible label: <label for=\"email\">Email</label> with <input id=\"email\">. "
                    "Then clicking the label focuses the input and a screen reader reads the label as the field's name; a "
                    "placeholder is not a label. Choose the input type by the data: email, tel, number, date, password, "
                    "checkbox, radio. On phones the type also picks the keyboard. Built-in validation attributes such as "
                    "required, min, max, minlength and pattern stop the form from being sent and show a message. They help "
                    "users, but the server must check again because browser checks can be bypassed. Inside a form, a <button> "
                    "has type=\"submit\" by default; use type=\"button\" only for buttons that must not send the form.",
        foundation=["label for = input id: the two values must match.",
                    "name = the key the server receives; id = the link to the label.",
                    "Browser validation is for convenience; the server still checks."],
        challenge="Build a sign-up form with an email, a password with minlength=\"8\" and a terms checkbox, then fill it in using "
                  "only the keyboard (Tab, Space, Enter) and fix anything you cannot reach.",
        example=dict(title="An accessible subscribe form", language="html",
                     code="<form action=\"/subscribe\" method=\"post\">\n  <label for=\"name\">Full name</label>\n"
                          "  <input id=\"name\" name=\"name\" type=\"text\" required>\n\n  <label for=\"email\">Email</label>\n"
                          "  <input id=\"email\" name=\"email\" type=\"email\" required>\n\n  <label>\n"
                          "    <input type=\"checkbox\" name=\"weekly\" value=\"yes\"> Send me the weekly job list\n  </label>\n\n"
                          "  <button type=\"submit\">Subscribe</button>\n</form>",
                     steps=["Each text input has a label whose for matches its id.",
                            "type=\"email\" checks the format and shows an email keyboard on phones.",
                            "A label can also wrap its input, as with the checkbox.",
                            "required stops sending until the field is filled; the submit button sends the form."]),
        career_examples=dict(data="Survey forms for data collection use the right input types so the answers arrive clean and comparable.",
                             software="Sign-up and checkout forms are where accessibility bugs cost real users; they are tested with keyboard and screen readers."),
        key_ideas=["Every input has a linked label.", "Pick the input type by the data.",
                   "required, min, max and pattern give built-in checks.", "The server must validate again."],
        mistakes=["Using placeholder text instead of a label.", "label for and input id that do not match, so the label is not linked."],
        practice="Write a contact form with name, email, a message (<textarea>) and a submit button, all with labels.",
        practical=dict(task="Build a job application form with at least five fields of different types, labels and validation rules.",
                       rubric=["Every field has a linked label", "Appropriate input types and validation attributes",
                               "Can be completed with the keyboard only"]),
        next_link="Next you will style pages with CSS: selectors, the cascade and the box model.",
        quiz=[
            dict(id="html-b2-q1", type="single", concept="labels",
                 prompt="How do you link a <label> to <input id=\"email\">?",
                 options=["<label name=\"email\">", "<label for=\"email\">", "<label id=\"email\">", "<label input=\"email\">"], answer=1,
                 explanation="The label's for attribute must equal the input's id."),
            dict(id="html-b2-q2", type="single", concept="input types",
                 prompt="Which input type checks the email format and shows an email keyboard on phones?",
                 options=["text", "email", "mail", "string"], answer=1,
                 explanation="type=\"email\" adds format validation and a suitable phone keyboard. mail and string are not input types."),
            dict(id="html-b2-q3", type="short", concept="labels",
                 prompt="In one sentence: why does every input need a label (not only a placeholder)?",
                 answer=[["screen reader", "assistive", "accessib", "blind"]],
                 sample_answer="A label tells screen reader users what the field is for and stays visible, and clicking it focuses the input.",
                 explanation="Labels give the field an accessible name for screen readers, stay visible while typing and make the click area bigger."),
        ],
        diagnostic=[
            dict(id="html-b2-d1", type="single", concept="buttons",
                 prompt="A <button> inside a <form> has no type attribute. What type is it?",
                 options=["button", "submit", "reset", "none"], answer=1,
                 explanation="The default type of a button in a form is submit, so it sends the form."),
            dict(id="html-b2-d2", type="single", concept="validation",
                 prompt="Which attribute stops the form from being sent while a field is empty?",
                 options=["required", "needed", "validate", "mandatory"], answer=0,
                 explanation="required is the built-in attribute; the others are not HTML attributes."),
        ],
    ),
    dict(
        id="html-i1", title="Selectors, the cascade and the box model", stage="Intermediate", requires=["html-b2"],
        objective="Predict which CSS rule wins (specificity and order) and how big an element is from content, padding, border, margin and box-sizing.",
        main_idea="CSS rules pick elements with selectors. When rules conflict, the more specific selector wins, then the later "
                  "rule. Every element is a box: content, padding, border and margin.",
        explanation="A rule is selector { property: value; }. Common selectors: element (p), class (.note), id (#intro), "
                    "descendant (nav a) and pseudo-classes (a:hover). When several rules set the same property on an element, "
                    "the cascade decides: first by importance (avoid !important), then by specificity (id beats class, class "
                    "beats element; inline styles beat all), then by order (the later rule wins). Some properties, such as "
                    "color and font, are inherited by children. The box model: content in the middle, then padding (space "
                    "inside the border), the border, and margin (space outside). With the default box-sizing: content-box, "
                    "width is only the content, so padding and border make the box wider. With box-sizing: border-box, width "
                    "includes padding and border, which makes layouts easier to predict. Many projects set "
                    "*, *::before, *::after { box-sizing: border-box; }. Vertical margins of blocks can collapse into one.",
        foundation=["Specificity order to remember: inline style > #id > .class > element.",
                    "Same specificity? The rule written later wins.",
                    "Box from inside out: content, padding, border, margin."],
        challenge="Open DevTools on a real site, find an element whose colour comes from a rule that was overridden, and explain "
                  "with specificity why the winning rule wins.",
        example=dict(title="Specificity and border-box", language="css",
                     code="* { box-sizing: border-box; }\n\np { color: blue; }\n.note { color: darkred; }\n\n.card {\n  width: 300px;\n"
                          "  padding: 16px;\n  border: 2px solid #ccc;\n  margin: 24px auto;\n}",
                     steps=["A <p class=\"note\"> matches both p and .note; .note (a class) is more specific, so it is dark red.",
                            "border-box makes the card exactly 300px wide, padding and border included.",
                            "The content area is 300 - 2x16 - 2x2 = 264px wide.",
                            "margin: 24px auto adds space above and below and centres the block horizontally."]),
        career_examples=dict(data="Dashboards often break when a chart's container is wider than expected; the box model explains why.",
                             software="Front-end bugs such as 'my style does not apply' are usually specificity problems, found with DevTools."),
        visual=dict(kind="table", caption="Who wins a conflict?", columns=["Selector", "Example", "Strength"],
                    rows=[["Inline style", "style=\"color: red\"", "strongest"], ["Id", "#intro", "strong"],
                          ["Class, attribute, pseudo-class", ".note, [type=email], :hover", "medium"], ["Element", "p, h2", "weak"]],
                    how_to_read="A stronger row beats a weaker row; if both rules are in the same row, the later rule wins."),
        key_ideas=["Specificity first, then source order.", "Avoid !important and long id chains.",
                   "content-box adds padding and border to the width; border-box includes them.", "Use DevTools to see the box and the winning rule."],
        mistakes=["Adding !important instead of understanding which rule wins.", "Forgetting that padding and border widen a content-box element."],
        practice="Give three elements different classes and an id, write conflicting colour rules and predict each colour before checking.",
        practical=dict(task="Style your portfolio page: a card layout with consistent spacing using border-box, and a colour scheme with classes.",
                       rubric=["border-box set globally", "No !important needed", "Spacing uses padding and margin consistently"]),
        next_link="Next you will lay out pages with flexbox and grid.",
        quiz=[
            dict(id="html-i1-q1", type="single", concept="box model",
                 prompt="box-sizing is content-box. The box has width: 200px, padding: 10px and border: 5px. How wide is it on screen?",
                 options=["200px", "215px", "230px", "220px"], answer=2,
                 explanation="200 + 2 x 10 (padding) + 2 x 5 (border) = 230px."),
            dict(id="html-i1-q2", type="single", concept="specificity",
                 prompt="Which selector has the highest specificity?",
                 options=["p", ".note", "#intro", "div p"], answer=2,
                 explanation="An id selector beats classes and element selectors."),
            dict(id="html-i1-q3", type="single", concept="cascade order",
                 prompt="Two rules with the same specificity set color on the same element. Which one applies?",
                 options=["The first one", "The one written later", "Neither", "The darker colour"], answer=1,
                 explanation="With equal specificity, the later rule in the CSS wins."),
        ],
        diagnostic=[
            dict(id="html-i1-d1", type="single", concept="box model",
                 prompt="box-sizing is border-box. The box has width: 200px and padding: 20px. How wide is it on screen?",
                 options=["200px", "240px", "160px", "220px"], answer=0,
                 explanation="With border-box, width includes padding and border, so the box is 200px (the content area is 160px)."),
            dict(id="html-i1-d2", type="single", concept="box model",
                 prompt="Which part of the box model is outside the border?",
                 options=["padding", "content", "margin", "the content box"], answer=2,
                 explanation="From inside out: content, padding, border, margin."),
        ],
    ),
    dict(
        id="html-i2", title="Flexbox and grid layout", stage="Intermediate", requires=["html-i1"],
        objective="Lay out rows, columns and page grids with flexbox (direction, justify, align, wrap, gap) and grid (template columns, fr, gap).",
        main_idea="Flexbox places items along one line and lets them share or wrap the space; grid places items on rows and columns "
                  "that you define. Both use gap for spacing.",
        explanation="display: flex makes the children flex items along the main axis: a row by default, or a column with "
                    "flex-direction: column. justify-content places items along the main axis (start, center, space-between); "
                    "align-items places them on the cross axis (stretch by default, center). flex-wrap: wrap lets items move to "
                    "a new line, and flex: 1 makes an item grow to fill space. display: grid with grid-template-columns: "
                    "1fr 2fr creates columns; fr means one share of the free space, and repeat(3, 1fr) makes three equal "
                    "columns. repeat(auto-fit, minmax(200px, 1fr)) creates as many columns as fit, which is responsive without "
                    "media queries. gap adds space between items in both. A simple rule of thumb: if the content should decide "
                    "the layout (a toolbar, tags), use flex; if the layout should decide where content goes (a page, a "
                    "gallery), use grid. Real pages often nest flex inside grid.",
        foundation=["Flex = one line of items; grid = rows and columns.",
                    "justify-content = along the main axis; align-items = across it.",
                    "fr = a share of the free space."],
        challenge="Build a card gallery with grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)) and explain why it needs "
                  "no media queries.",
        example=dict(title="A header with flex and a gallery with grid", language="css",
                     code=".site-header {\n  display: flex;\n  justify-content: space-between;\n  align-items: center;\n  gap: 16px;\n}\n\n"
                          ".gallery {\n  display: grid;\n  grid-template-columns: repeat(3, 1fr);\n  gap: 24px;\n}",
                     steps=["The header puts the logo and nav in a row, pushed to the two ends by space-between.",
                            "align-items: center lines them up vertically.",
                            "The gallery has three equal columns; items fill them row by row.",
                            "gap adds the space between items, so no margins are needed on the children."]),
        career_examples=dict(data="Analytics dashboards are grids of chart cards; grid keeps them aligned at every screen size.",
                             software="Almost every UI component (navbars, cards, forms) is laid out with flex or grid in modern front-end code."),
        key_ideas=["display: flex for one-dimensional rows or columns.", "display: grid for rows and columns together.",
                   "justify = main axis, align = cross axis.", "Use gap instead of margins between items."],
        mistakes=["Using justify-items in a flex container (flexbox ignores it).", "Using floats or fixed pixel widths for page layout."],
        practice="Lay out a navigation bar with flex and a three-column product list with grid.",
        practical=dict(task="Lay out your portfolio: a flex header, a grid of project cards and a footer, using gap for spacing.",
                       rubric=["Flex used for the header", "Grid used for the cards", "No floats or margin hacks for layout"]),
        next_link="Next you will make the layout work on every screen size with responsive design.",
        quiz=[
            dict(id="html-i2-q1", type="single", concept="flex direction",
                 prompt="Which declaration places flex items in a column?",
                 options=["flex-direction: column", "display: column", "align-items: column", "flex-wrap: column"], answer=0,
                 explanation="flex-direction sets the main axis; column makes it vertical."),
            dict(id="html-i2-q2", type="single", concept="flex alignment",
                 prompt="In a row flex container, which property centres the items left to right (along the main axis)?",
                 options=["align-items: center", "justify-content: center", "text-align: center", "justify-items: center"], answer=1,
                 explanation="justify-content works on the main axis. align-items works on the cross axis, and flexbox ignores justify-items.",
                 why_wrong={0: "align-items works on the cross axis (vertical in a row).", 3: "justify-items is ignored by flexbox; it is for grid."}),
            dict(id="html-i2-q3", type="single", concept="grid fr",
                 prompt="A grid container is 300px wide with grid-template-columns: 1fr 2fr and no gap. How wide is the second column?",
                 options=["100px", "150px", "200px", "300px"], answer=2,
                 explanation="1fr + 2fr = 3 shares of 300px, so one share is 100px and 2fr is 200px."),
        ],
        diagnostic=[
            dict(id="html-i2-d1", type="single", concept="flex or grid",
                 prompt="You need a page layout with a sidebar, header, content and footer placed on rows and columns. Which tool fits best?",
                 options=["Flexbox", "Grid", "float", "inline-block"], answer=1,
                 explanation="Grid defines rows and columns together, so the layout decides where each part goes."),
            dict(id="html-i2-d2", type="single", concept="gap",
                 prompt="What does gap: 16px do in a flex or grid container?",
                 options=["Adds 16px of space between the items", "Adds 16px of padding around the container",
                          "Adds a margin to the page", "Sets the minimum item width"], answer=0,
                 explanation="gap sets the space between items (rows and columns), not around the container."),
        ],
    ),
    dict(
        id="html-a1", title="Responsive design", stage="Advanced", requires=["html-i2"],
        objective="Make pages work on phones and desktops with the viewport meta tag, mobile-first media queries, relative units and responsive images.",
        main_idea="A responsive page adapts to the screen. Write the phone layout first, then add rules for wider screens with "
                  "min-width media queries, and use flexible units and images.",
        explanation="Without <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">, phones draw the page at a "
                    "desktop width (often 980px) and zoom out, so text is tiny and small-screen media queries never apply. "
                    "Mobile-first CSS writes the base styles for small screens, then adds @media (min-width: 600px) { ... } "
                    "and @media (min-width: 1000px) { ... } for wider screens; when several queries match, the later rule "
                    "wins, so list them from small to large. Use relative units: rem (relative to the root font size, so it "
                    "follows the user's browser setting), %, and vw/vh for viewport sizes; max-width: 60ch keeps lines readable. "
                    "Images: img { max-width: 100%; height: auto; } stops them overflowing, and srcset/sizes let the browser "
                    "download a smaller file on phones. Modern layouts need fewer breakpoints: flex-wrap and "
                    "grid repeat(auto-fit, minmax(...)) adapt on their own. Test with the DevTools device toolbar and on a real phone.",
        foundation=["Mobile first: phone styles first, then min-width queries for bigger screens.",
                    "min-width: 768px means '768px wide or more'.",
                    "No viewport meta tag = phones pretend to be desktops."],
        challenge="Make your portfolio work from 320px to 1440px wide with at most two media queries, using rem units and a grid "
                  "with auto-fit for the project cards.",
        example=dict(title="Mobile-first job cards", language="css",
                     code="img { max-width: 100%; height: auto; }\n\n.cards {\n  display: grid;\n  grid-template-columns: 1fr;\n"
                          "  gap: 1rem;\n}\n\n@media (min-width: 600px) {\n  .cards { grid-template-columns: 1fr 1fr; }\n}\n\n"
                          "@media (min-width: 1000px) {\n  .cards { grid-template-columns: repeat(3, 1fr); }\n}",
                     steps=["Phones get one column: the base rule, with no media query.",
                            "From 600px the first query adds a second column.",
                            "From 1000px both queries match; the later one wins, so there are three columns.",
                            "Images never get wider than their container."]),
        career_examples=dict(data="Stakeholders open dashboards on phones; a responsive layout keeps the key numbers readable.",
                             software="Most web traffic is mobile, so responsive layouts are checked in every front-end code review and QA pass."),
        key_ideas=["Always include the viewport meta tag.", "Mobile first with min-width queries, ordered small to large.",
                   "Prefer rem, %, and flexible layouts over fixed px widths.", "Images: max-width: 100% and srcset."],
        mistakes=["Fixed widths such as width: 1200px that cause sideways scrolling on phones.",
                  "Ordering min-width queries from large to small, so the wrong rule wins."],
        practice="Take a fixed-width page and make it responsive with the viewport tag, one media query and max-width images.",
        practical=dict(task="Make your full portfolio page responsive and test it at 360px, 768px and 1280px in the DevTools device toolbar.",
                       rubric=["No sideways scrolling at 360px", "Layout changes sensibly at the breakpoints", "Uses relative units and responsive images"]),
        next_link="You can now build accessible, responsive pages. Next on the roadmap: interactivity with JavaScript.",
        quiz=[
            dict(id="html-a1-q1", type="single", concept="viewport meta",
                 prompt="A page has no viewport meta tag. What usually happens on a phone?",
                 options=["The page is drawn at a desktop width and zoomed out, so small-screen media queries do not apply",
                          "The page is hidden", "The browser uses the print styles", "The CSS is blocked"], answer=0,
                 explanation="Phones then assume the page is not responsive and use a wide layout viewport (often 980px)."),
            dict(id="html-a1-q2", type="single", concept="mobile first",
                 prompt="What does mobile-first CSS mean?",
                 options=["Base styles for small screens, then min-width media queries for wider screens",
                          "Desktop styles first, then max-width queries for phones", "Using only px units", "A separate site for phones"], answer=0,
                 explanation="Mobile first starts simple and adds layout as space grows, with min-width queries."),
            dict(id="html-a1-q3", type="multi", concept="responsive images",
                 prompt="Which help images work on small screens? Select all that apply.",
                 options=["max-width: 100%", "height: auto", "width: 1200px", "srcset with several image sizes"], answer=[0, 1, 3],
                 explanation="max-width: 100% with height: auto keeps images inside their container with the right shape; srcset "
                             "lets phones download smaller files. A fixed 1200px width overflows."),
        ],
        diagnostic=[
            dict(id="html-a1-d1", type="single", concept="media queries",
                 prompt="When does @media (min-width: 768px) { ... } apply?",
                 options=["When the viewport is at least 768px wide", "When it is at most 768px wide", "Only at exactly 768px",
                          "Only when printing"], answer=0,
                 explanation="min-width means the minimum width: 768px or wider."),
            dict(id="html-a1-d2", type="single", concept="relative units",
                 prompt="What is 1rem equal to?",
                 options=["The font size of the root (html) element", "The parent element's font size", "1% of the viewport width",
                          "Always 16px"], answer=0,
                 explanation="rem is relative to the root font size (16px by default, but users can change it). em is relative to the parent; vw to the viewport."),
        ],
    ),
]
