# Owner: Dewmi - Component 04. Curated lesson bank for JavaScript (SK004). Drafted with an AI assistant, checked by the curriculum validator and tests, and reviewed by the C4 author.
SKILL_ID = "SK004"

TOPICS = [
    dict(
        id="js-b1", title="Values, variables and types", stage="Beginner", requires=[],
        objective="Store values with const and let, know the basic types, build text with template literals and compare with ===.",
        main_idea="JavaScript values have types (number, string, boolean, undefined, null, object). Use const by default, let when "
                  "the value must change, and === so no hidden type conversion surprises you.",
        explanation="const name = \"Ama\"; creates a variable that cannot be reassigned; let score = 7; can be changed later. Avoid "
                    "var (older, function-scoped, see the closures topic). typeof tells you the type: typeof 7 is \"number\", "
                    "typeof \"7\" is \"string\". Numbers include decimals (there is one number type). Build text with template "
                    "literals: `${name} has ${score} points`. JavaScript converts types automatically in some operations: + "
                    "with a string joins text (\"4\" + 2 is \"42\"), while -, * and / convert strings to numbers (\"4\" - 2 is 2). "
                    "Form inputs always give strings, so convert them with Number(value). == compares after converting types "
                    "(\"5\" == 5 is true); === compares value and type with no conversion (\"5\" === 5 is false), so use === and "
                    "!==. undefined means 'no value assigned yet'; null means 'deliberately empty'.",
        foundation=["const by default; let only when you will reassign.",
                    "Text in quotes is a string, even \"42\".",
                    "Always === and !==."],
        challenge="Write a function that takes a value from a form field (a string) and returns a number or a clear error "
                  "message, handling \"\", \"12\", \"12.5\" and \"abc\" (hint: Number and Number.isNaN).",
        example=dict(title="Values and comparisons", language="javascript",
                     code="const name = \"Ama\";\nlet score = 7;\nscore = score + 1;\n"
                          "console.log(`${name} has ${score} points`);   // Ama has 8 points\n"
                          "console.log(typeof score, typeof name);       // number string\n"
                          "console.log(\"5\" == 5, \"5\" === 5);             // true false\n"
                          "console.log(Number(\"12\") + 3);                // 15",
                     steps=["name never changes, so it is const; score changes, so it is let.",
                            "The template literal puts both values into the text.",
                            "== converts \"5\" to 5 before comparing; === does not, so it is false.",
                            "Number(\"12\") converts the string first, so + adds instead of joining."]),
        career_examples=dict(data="Data from CSV files and APIs often arrives as strings; converting types is a daily data-cleaning step.",
                             software="Many front-end bugs come from string values read from forms being joined instead of added."),
        visual=dict(kind="table", caption="Operators and types", columns=["Expression", "Result", "Why"],
                    rows=[["\"4\" + 2", "\"42\"", "+ with a string joins text"], ["\"4\" - 2", "2", "- converts to numbers"],
                          ["\"5\" == 5", "true", "== converts types first"], ["\"5\" === 5", "false", "=== also compares the type"]],
                    how_to_read="Read each row left to right: the expression, what JavaScript gives, and the rule behind it."),
        key_ideas=["const by default, let when the value changes.", "+ joins strings; convert input with Number().",
                   "Use === and !==.", "Template literals build readable text."],
        mistakes=["Adding form values without converting them, so 10 + \"5\" becomes \"105\".", "Using == and getting surprising true results."],
        practice="Write a small script that stores a product name and price, applies a discount and prints a sentence with a template literal.",
        practical=dict(task="Write a tip calculator script: bill and tip percentage as strings (like form values), converted, calculated and printed.",
                       rubric=["Inputs converted with Number()", "Uses const/let correctly", "Output built with a template literal"]),
        next_link="Next you will group code into functions and work with arrays and objects.",
        quiz=[
            dict(id="js-b1-q1", type="single", concept="const and let",
                 prompt="What happens when this runs?  const total = 10;  total = 12;",
                 options=["total becomes 12", "TypeError: Assignment to constant variable", "total stays 10 with no error",
                          "Nothing happens"], answer=1,
                 explanation="A const variable cannot be reassigned; JavaScript throws a TypeError. Use let if the value must change."),
            dict(id="js-b1-q2", type="single", concept="type conversion",
                 prompt="What is the value of \"5\" + 3?",
                 options=["8", "\"53\" (a string)", "NaN", "TypeError"], answer=1,
                 explanation="+ with a string joins text, so 3 becomes \"3\" and the result is \"53\"."),
            dict(id="js-b1-q3", type="single", concept="strict equality",
                 prompt="Which comparison should you use by default?",
                 options=["== because it converts types", "=== because it compares value and type without conversion",
                          "= because it is shorter", "!= in every case"], answer=1,
                 explanation="=== avoids hidden conversions. = is assignment, not comparison.",
                 why_wrong={2: "= assigns a value; it does not compare."}),
        ],
        diagnostic=[
            dict(id="js-b1-d1", type="single", concept="const and let",
                 prompt="Which keyword is right for a loop counter that changes every round?",
                 options=["const", "let", "static", "final"], answer=1,
                 explanation="let allows reassignment; const does not. static and final are not used to declare variables in JavaScript."),
            dict(id="js-b1-d2", type="single", concept="type conversion",
                 prompt="What is the value of \"5\" - 2?",
                 options=["3", "\"52\"", "NaN", "\"5-2\""], answer=0,
                 explanation="- only works on numbers, so \"5\" is converted to 5 and the result is the number 3."),
        ],
    ),
    dict(
        id="js-b2", title="Functions, arrays and objects", stage="Beginner", requires=["js-b1"],
        objective="Write functions and arrow functions, use map, filter and reduce on arrays, and read and destructure objects.",
        main_idea="Functions package steps you can reuse. Arrays hold lists; objects hold named properties. map, filter and reduce "
                  "transform lists without changing the original.",
        explanation="function add(a, b) { return a + b; } and the arrow form const add = (a, b) => a + b; both take parameters "
                    "and return a value (an arrow function with no braces returns its expression). Arrays: const marks = [72, 45, 88]; "
                    "marks.length is 3, marks[0] is 72, marks.push(90) adds one. Objects group data: const student = "
                    "{ name: \"Ama\", mark: 72 }; read with student.name, and destructure with const { name, mark } = student;. "
                    "The array methods take a function: filter keeps the items for which it returns true, map returns a new "
                    "array of transformed items, reduce combines all items into one value starting from an initial value: "
                    "marks.reduce((sum, m) => sum + m, 0). They return new values and leave the original array unchanged, "
                    "which makes code easier to follow. Functions are values: you can pass them to other functions, as "
                    "map and addEventListener expect.",
        foundation=["filter = keep some; map = change each; reduce = combine into one.",
                    "An arrow function without { } returns its expression.",
                    "Read an object property with a dot: student.name."],
        challenge="Given an array of order objects, write one chain that returns the total value of paid orders over 1000, "
                  "using filter, map and reduce, and explain each step.",
        example=dict(title="Pass list and average", language="javascript",
                     code="const students = [\n  { name: \"Ama\", mark: 72 },\n  { name: \"Ben\", mark: 45 },\n  { name: \"Chen\", mark: 88 },\n];\n"
                          "const passed = students.filter(s => s.mark >= 50);\nconst names = passed.map(s => s.name);\n"
                          "const total = students.reduce((sum, s) => sum + s.mark, 0);\n"
                          "console.log(names.join(\", \"));            // Ama, Chen\n"
                          "console.log(total / students.length);    // 68.33333333333333",
                     steps=["filter keeps the students with a mark of 50 or more.",
                            "map turns each kept object into just its name.",
                            "reduce adds all marks, starting from 0: 205.",
                            "The original students array is not changed."]),
        career_examples=dict(data="Analysts reshape JSON from APIs with map and filter before charting it.",
                             software="Front-end code renders lists by mapping an array of objects to UI elements (for example in React)."),
        key_ideas=["Functions take parameters and return values.", "Arrow functions are short and common.",
                   "map/filter/reduce return new values.", "Objects hold named properties; destructuring reads several at once."],
        mistakes=["Forgetting the initial value of reduce (0), which breaks on an empty array.", "Expecting map to change the original array."],
        practice="Given an array of prices, return the prices with tax (map), only those under 1000 (filter), and their sum (reduce).",
        practical=dict(task="Write functions that take an array of job objects (title, salary, remote) and return remote jobs, their titles and the average salary.",
                       rubric=["Each function does one job", "Uses map, filter and reduce correctly", "Original array is not modified"]),
        next_link="Next you will make pages interactive with the DOM and events.",
        quiz=[
            dict(id="js-b2-q1", type="single", concept="map",
                 prompt="What does [1, 2, 3].map(n => n * 2) return?",
                 options=["A new array [2, 4, 6]", "6", "undefined", "It changes the original array to [2, 4, 6] and returns nothing"], answer=0,
                 explanation="map returns a new array with each item transformed; the original stays [1, 2, 3]."),
            dict(id="js-b2-q2", type="single", concept="filter",
                 prompt="Which method keeps only the items that pass a test?",
                 options=["map", "filter", "reduce", "push"], answer=1,
                 explanation="filter keeps the items for which the function returns true."),
            dict(id="js-b2-q3", type="single", concept="destructuring",
                 prompt="What does const { name, mark } = student; do?",
                 options=["Creates the variables name and mark from student's properties", "Deletes those properties",
                          "Creates a copy of student called name", "Causes a SyntaxError"], answer=0,
                 explanation="Object destructuring reads the properties with the same names into new variables."),
        ],
        diagnostic=[
            dict(id="js-b2-d1", type="single", concept="arrow functions",
                 prompt="const next = x => x + 1;  What does next(4) return?",
                 options=["5", "undefined", "\"x + 1\"", "4"], answer=0,
                 explanation="An arrow function without braces returns its expression: 4 + 1 = 5."),
            dict(id="js-b2-d2", type="single", concept="reduce",
                 prompt="In marks.reduce((sum, m) => sum + m, 0), what is the 0?",
                 options=["The starting value of sum", "The index to start from", "The number of items", "The value to remove"], answer=0,
                 explanation="The second argument of reduce is the initial value of the accumulator (sum)."),
        ],
    ),
    dict(
        id="js-i1", title="The DOM and events", stage="Intermediate", requires=["js-b2"],
        objective="Select elements, change their text and classes, and respond to clicks and form submits with addEventListener and preventDefault.",
        main_idea="The browser turns HTML into the DOM, a tree of objects. JavaScript finds elements, changes them, and runs "
                  "functions (listeners) when events such as click or submit happen.",
        explanation="document.querySelector(\".card\") returns the first element matching a CSS selector (or null); "
                    "querySelectorAll returns all of them. Change content safely with element.textContent = \"Saved\" (it "
                    "inserts text, never HTML); innerHTML parses HTML, so never use it with user input (it allows script "
                    "injection). Change styles through classes: element.classList.add(\"active\"), .remove, .toggle. "
                    "React to events with element.addEventListener(\"click\", handler): pass the function itself (handler), "
                    "not handler(), which would call it immediately. Several listeners can be added to one element and all "
                    "run. The handler receives an event object: event.target is the element that was clicked, and "
                    "event.preventDefault() cancels the browser's default action, for example sending a form and reloading the "
                    "page so you can check it first. Events bubble up to parents, so one listener on a list can handle clicks "
                    "on all its items (event delegation). Put scripts at the end of body or use <script defer> so the elements exist.",
        foundation=["querySelector uses the same selectors as CSS.",
                    "textContent for text; classList for styles.",
                    "addEventListener(\"click\", doThing) - no brackets after doThing."],
        challenge="Build a to-do list where one click listener on the <ul> (event delegation) marks items done with classList.toggle, "
                  "including items added later.",
        example=dict(title="A form with a live message", language="javascript",
                     code="const form = document.querySelector(\"#signup\");\nconst message = document.querySelector(\"#message\");\n\n"
                          "form.addEventListener(\"submit\", (event) => {\n  event.preventDefault();\n"
                          "  const email = form.elements.email.value.trim();\n  if (email === \"\") {\n"
                          "    message.textContent = \"Please enter your email.\";\n    message.classList.add(\"error\");\n  } else {\n"
                          "    message.textContent = `Thanks, ${email}!`;\n    message.classList.remove(\"error\");\n  }\n});",
                     steps=["querySelector finds the form and the message element by id.",
                            "The submit listener runs when the user submits; preventDefault stops the page reload.",
                            "textContent shows the message as plain text, safe even with user input.",
                            "classList switches the error style on and off."]),
        career_examples=dict(data="Interactive charts react to hover and click events to show details of a data point.",
                             software="Every button, form and menu in a web app is wired up with event listeners."),
        key_ideas=["The DOM is the page as objects.", "querySelector + textContent + classList cover most changes.",
                   "Pass the function, do not call it.", "preventDefault stops the browser's default action."],
        mistakes=["Writing addEventListener(\"click\", save()) so save runs at once.", "Using innerHTML with user input (security risk)."],
        practice="Make a button that counts clicks and shows the count in a <span>, and a second button that resets it.",
        practical=dict(task="Add JavaScript to your form page: check the fields on submit, show messages with textContent and highlight errors with a class.",
                       rubric=["Uses addEventListener and preventDefault", "Updates the page with textContent and classList",
                               "No innerHTML with user input"]),
        next_link="Next you will load data from servers with promises, async/await and fetch.",
        quiz=[
            dict(id="js-i1-q1", type="single", concept="selecting elements",
                 prompt="Which line selects the first element with the class card?",
                 options=["document.querySelector(\".card\")", "document.querySelector(\"card\")", "document.getElementById(\".card\")",
                          "document.querySelectorAll(\"#card\")"], answer=0,
                 explanation="querySelector takes a CSS selector, and .card means 'class card'. \"card\" would look for a <card> element."),
            dict(id="js-i1-q2", type="single", concept="safe updates",
                 prompt="You want to show a user's comment on the page. Which property should you set?",
                 options=["textContent, because it inserts text, not HTML, so the comment cannot inject markup or scripts",
                          "innerHTML, because it is always safer", "Either one, they are the same", "Neither can change the page"], answer=0,
                 explanation="textContent treats the value as plain text. innerHTML parses HTML, which allows script injection (XSS)."),
            dict(id="js-i1-q3", type="single", concept="preventDefault",
                 prompt="What does event.preventDefault() do in a form's submit listener?",
                 options=["Stops the browser's default action: sending the form and reloading the page", "Stops all other listeners",
                          "Deletes the form", "Sends the form twice"], answer=0,
                 explanation="It cancels the default action, so your JavaScript can check or send the data itself."),
        ],
        diagnostic=[
            dict(id="js-i1-d1", type="single", concept="passing listeners",
                 prompt="What is wrong with button.addEventListener(\"click\", save());?",
                 options=["save runs immediately and its return value is used as the listener; pass save without ()",
                          "Nothing is wrong", "\"click\" must be in capitals", "addEventListener needs three arguments"], answer=0,
                 explanation="addEventListener needs the function itself. save() calls it straight away."),
            dict(id="js-i1-d2", type="single", concept="event delegation",
                 prompt="What is event delegation?",
                 options=["One listener on a parent handles events from its children, using event.target",
                          "Each child gets its own copy of the listener", "Delaying events with setTimeout",
                          "Removing all listeners from a page"], answer=0,
                 explanation="Events bubble up to parents, so one parent listener can handle all children, including ones added later."),
        ],
    ),
    dict(
        id="js-i2", title="Async JavaScript: promises, async/await and fetch", stage="Intermediate", requires=["js-i1"],
        objective="Explain the order in which async code runs, use async/await with try/catch, and call fetch and check response.ok.",
        main_idea="Slow work (network, timers) does not block JavaScript; it finishes later and gives back a promise. async/await "
                  "lets you write that code step by step, and try/catch handles its errors.",
        explanation="JavaScript runs one piece of code at a time. Slow operations return a Promise: a value that will be ready "
                    "later (fulfilled) or fail (rejected). The event loop runs all normal code first, then promise callbacks "
                    "(.then, code after await), then timer callbacks (setTimeout), even with a 0 ms delay. An async function "
                    "always returns a promise; inside it, await pauses that function (not the page) until the promise is "
                    "settled and gives its value. fetch(url) returns a promise for a Response. fetch only rejects on a network "
                    "failure: a 404 or 500 response still fulfils, so check response.ok (or response.status) and throw or "
                    "show a message. response.json() is also asynchronous and needs await. Wrap awaited calls in try/catch; "
                    "a promise that is not awaited cannot be caught by try/catch and becomes an unhandled rejection. "
                    "Promise.all([...]) waits for several requests in parallel.",
        foundation=["A promise = a receipt for a value that comes later.",
                    "await only inside an async function (or at the top of an ES module).",
                    "fetch: check response.ok, then await response.json()."],
        challenge="Load two endpoints in parallel with Promise.all, show both results, and show one friendly error if either "
                  "request fails or returns a non-OK status.",
        example=dict(title="Loading jobs from an API", language="javascript",
                     code="async function loadJobs() {\n  try {\n    const response = await fetch(\"/api/jobs\");\n"
                          "    if (!response.ok) {\n      throw new Error(`Server answered ${response.status}`);\n    }\n"
                          "    const jobs = await response.json();\n    console.log(`${jobs.length} jobs loaded`);\n"
                          "  } catch (err) {\n    console.log(\"Could not load jobs:\", err.message);\n  }\n}\n\nloadJobs();",
                     steps=["await fetch waits for the response without freezing the page.",
                            "A 404 or 500 does not reject, so response.ok is checked and an error is thrown.",
                            "await response.json() reads and parses the body.",
                            "catch handles both network errors and the thrown error in one place."]),
        career_examples=dict(data="Dashboards fetch fresh data from APIs and must show a clear message when a request fails.",
                             software="Every single-page app loads data with fetch (or a library on top of it) and handles loading and error states."),
        key_ideas=["Normal code first, then promise callbacks, then timers.", "async functions return promises; await waits for them.",
                   "fetch does not reject on 404: check response.ok.", "Use try/catch around awaited calls."],
        mistakes=["Forgetting await, so the variable holds a Promise instead of the data.", "Treating any fetch response as success without checking response.ok."],
        practice="Write an async function that fetches a JSON file, checks response.ok, and prints one field, with a try/catch.",
        practical=dict(task="Load a list of items from a public JSON API into your page, with a loading message and an error message.",
                       rubric=["Uses async/await and checks response.ok", "Errors are caught and shown to the user",
                               "Loading state is shown while waiting"]),
        next_link="Next you will organise larger programs with scope, closures and modules.",
        quiz=[
            dict(id="js-i2-q1", type="single", concept="async functions",
                 prompt="What does an async function always return?",
                 options=["A Promise", "The value directly", "undefined", "A callback function"], answer=0,
                 explanation="An async function wraps its return value in a promise (and a thrown error in a rejected promise)."),
            dict(id="js-i2-q2", type="single", concept="fetch errors",
                 prompt="fetch(\"/api/user/99\") gets a 404 Not Found response. What does the promise do?",
                 options=["It fulfils with a Response whose ok is false, so you must check response.ok", "It rejects automatically",
                          "It throws a SyntaxError", "It returns null"], answer=0,
                 explanation="fetch only rejects on network failure; HTTP error statuses still give a Response."),
            dict(id="js-i2-q3", type="multi", concept="handling errors",
                 prompt="Which are good ways to handle errors from await fetch(...)? Select all that apply.",
                 options=["Wrap the await in try/catch", "Check response.ok and throw or show a message when it is false",
                          "Do nothing, because fetch never fails", "Add .catch() to the promise returned by the async function"], answer=[0, 1, 3],
                 explanation="try/catch, checking response.ok and .catch() on the returned promise all handle failures. Requests do fail."),
        ],
        diagnostic=[
            dict(id="js-i2-d1", type="single", concept="await",
                 prompt="Where can you use await?",
                 options=["Inside an async function (or at the top level of an ES module)", "Anywhere in any script",
                          "Only inside loops", "Only with setTimeout"], answer=0,
                 explanation="await is allowed in async functions and at the top level of modules; in a plain script it is a SyntaxError."),
            dict(id="js-i2-d2", type="single", concept="event loop",
                 prompt="When does the callback of setTimeout(f, 0) run?",
                 options=["After the current code and the already-queued promise callbacks have finished",
                          "Immediately, before the next line", "Never", "After exactly 0 ms, interrupting the current code"], answer=0,
                 explanation="Timers wait for the current code and the promise (microtask) queue, even with a 0 ms delay."),
        ],
    ),
    dict(
        id="js-a1", title="Scope, closures and modules", stage="Advanced", requires=["js-i2"],
        objective="Explain block scope and closures, split code into ES modules with named and default exports, and throw and catch custom errors.",
        main_idea="Each variable lives in a scope. A function remembers the scope where it was created (a closure). Modules give "
                  "each file its own scope and share only what it exports.",
        explanation="let and const are block-scoped: a variable declared inside { } (an if, a loop) does not exist outside it. "
                    "var is function-scoped, so a var in a loop is one shared variable for the whole function, which is why "
                    "old code had bugs with loops and callbacks; prefer let and const. A closure is a function together with "
                    "the variables of the scope it was created in: makeCounter() can return a function that keeps its own "
                    "count, private to that function and separate for every call of makeCounter. Closures power event "
                    "handlers, callbacks and private state. ES modules: each file has its own top-level scope. export const "
                    "TAX_RATE = 0.1; is a named export, imported with the same name in braces: import { TAX_RATE } from "
                    "\"./prices.js\";. A module can have at most one default export (export default function withTax() {...}), "
                    "imported without braces under any name: import withTax from \"./prices.js\";. Browsers load modules with "
                    "<script type=\"module\">. Errors: throw new Error(\"message\") stops normal flow until a try/catch handles "
                    "it. A custom error class (class ValidationError extends Error) lets catch tell kinds of errors apart "
                    "with instanceof.",
        foundation=["{ } makes a block; let and const stay inside it.",
                    "A closure = a function plus the variables it remembers.",
                    "Named export -> import { name }; default export -> import anyName."],
        challenge="Split a small app into three modules (api.js, format.js, main.js) with named and default exports, and add a "
                  "ValidationError class that main.js catches separately from other errors.",
        example=dict(title="A private counter and a module", language="javascript",
                     code="// counter.js\nexport default function makeCounter() {\n  let count = 0;          // private to this counter\n"
                          "  return () => {\n    count = count + 1;\n    return count;\n  };\n}\n"
                          "export class LimitError extends Error {}\n\n// main.js\n"
                          "import makeCounter, { LimitError } from \"./counter.js\";\n\nconst next = makeCounter();\n"
                          "try {\n  if (next() > 0 && next() > 1) {\n    throw new LimitError(\"Only one click allowed\");\n  }\n"
                          "} catch (err) {\n  if (err instanceof LimitError) console.log(err.message);\n  else throw err;\n}",
                     steps=["count is created inside makeCounter, so only the returned function can see and change it.",
                            "makeCounter is the default export; LimitError is a named export, imported in braces.",
                            "The second call returns 2, so a LimitError is thrown.",
                            "catch checks the error type with instanceof and re-throws errors it does not expect."]),
        career_examples=dict(data="Data visualisation code is split into modules (loading, cleaning, charting) so each part can be tested.",
                             software="Every modern front-end and Node.js project is organised in ES modules; closures appear in every callback and React hook."),
        key_ideas=["let/const are block-scoped; avoid var.", "Closures keep variables alive and private.",
                   "Named exports use braces; one default export per module.", "Throw specific errors and catch them deliberately."],
        mistakes=["Using var in a loop with callbacks, so every callback sees the last value.",
                  "Importing a default export with braces (or a named export without them)."],
        practice="Write makeTimer() that returns start and stop functions sharing a private start time, and export it from a module.",
        practical=dict(task="Refactor one of your scripts into at least two ES modules with a private helper (not exported) and a custom error type.",
                       rubric=["Uses named and default exports correctly", "No var; block scope used deliberately",
                               "A custom error is thrown and handled with instanceof"]),
        next_link="You now have the JavaScript base for frameworks such as React and for Node.js on the server.",
        quiz=[
            dict(id="js-a1-q1", type="single", concept="block scope",
                 prompt="What happens?  if (true) { let x = 1; }  console.log(x);",
                 options=["It prints 1", "It prints undefined", "ReferenceError: x is not defined", "It prints null"], answer=2,
                 explanation="let is block-scoped, so x does not exist outside the if block."),
            dict(id="js-a1-q2", type="single", concept="modules",
                 prompt="prices.js has export default function withTax() {...} and export const TAX_RATE = 0.1;. Which import is correct?",
                 options=["import withTax, { TAX_RATE } from \"./prices.js\";", "import { withTax, TAX_RATE } from \"./prices.js\";",
                          "import withTax, TAX_RATE from \"./prices.js\";", "require withTax from \"./prices.js\";"], answer=0,
                 explanation="The default export is imported without braces; the named export TAX_RATE goes in braces.",
                 why_wrong={1: "withTax is the default export, not a named export called withTax."}),
            dict(id="js-a1-q3", type="multi", concept="closures",
                 prompt="Which statements about closures are true? Select all that apply.",
                 options=["A function remembers the variables of the scope where it was created", "Each call of makeCounter() gets its own count",
                          "A closure copies a variable's value once and never sees later changes", "Closures can keep data private"],
                 answer=[0, 1, 3],
                 explanation="A closure keeps a live link to the variables (not a copy), each call creates a new scope, and code "
                             "outside cannot reach those variables."),
        ],
        diagnostic=[
            dict(id="js-a1-d1", type="single", concept="custom errors",
                 prompt="class ValidationError extends Error {}  try { throw new ValidationError(\"Email missing\"); } catch (e) "
                        "{ console.log(e instanceof ValidationError, e.message); }  What is printed?",
                 options=["true Email missing", "false Email missing", "true undefined", "Nothing: the error crashes the program"], answer=0,
                 explanation="The thrown object is a ValidationError (and an Error), and the message passed to the constructor is kept."),
            dict(id="js-a1-d2", type="single", concept="modules",
                 prompt="How many default exports can one module have?",
                 options=["At most one", "Any number", "Exactly two", "None; only named exports exist"], answer=0,
                 explanation="A module has at most one default export and any number of named exports."),
        ],
    ),
]
