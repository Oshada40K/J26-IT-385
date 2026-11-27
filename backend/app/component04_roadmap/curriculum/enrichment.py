# Owner: Dewmi - Component 04. Extra teaching parts for every curated topic, used by the "lecture notes" lesson style:
#   from_zero    - an everyday analogy that explains the idea to a complete beginner
#   memory_trick - a short way to remember it
#   career_hack  - an interview / workplace tip (how the idea is checked in real jobs)
#   recall       - memory-test questions; the answer is hidden until the student reveals it (practice, not graded)
#   video        - one short YouTube video; title and channel are copied exactly from YouTube oEmbed on checked_on
#   exercises    - interactive practice exercises (EXERCISES at the end of this file), checked on the server; practice
#                  only, never evidence. See EXERCISES for how they were written and verified.
# Drafted with an AI assistant, checked by the curriculum validator and tests, and reviewed by the C4 author. Merged into the topics by curriculum.load().

ENRICHMENT = {
    # ------------------------------------------------------------------ Programming Fundamentals (SK001)
    "pf-b1": dict(
        from_zero="Think of a recipe. It lists exact steps in order (algorithm), uses containers that hold ingredients (variables), "
                  "says 'if the sauce is too thick, add water' (decision) and 'stir every minute until it boils' (loop). A program "
                  "is the same: exact steps, named values, choices and repetition.",
        memory_trick="S-V-D-L: Steps, Variables, Decisions, Loops. Every program is built from these four.",
        career_hack="In interviews, say the steps out loud or write pseudocode before coding. Interviewers score your plan, not only the final code.",
        recall=[dict(q="What are the four building blocks of every program?", a="Ordered steps, variables, decisions (if/else) and loops."),
                dict(q="In an if / elif / else chain, how many branches run?", a="Exactly one: the first condition that is true, or else.")],
        video=dict(youtube_id="K-8pcXYcTQQ", title="Basic Programming Concepts: Variables, Loops, Functions, Inputs/Outputs, Object Oriented Programming",
                   channel="Zachary Fruhling (Fruhling Designs / CozyAzeroth)", minutes=7, checked_on="2026-11-06",
                   why="Introduces variables, loops, functions, inputs and outputs, and how to think like a programmer.")),
    "pf-b2": dict(
        from_zero="Cleaning a whole house feels hard; 'clean the kitchen', 'clean the bedroom' and 'take out the rubbish' are easy. "
                  "Each small job is a function: it has a name, it gets what it needs (parameters) and it gives something back (return value).",
        memory_trick="One function, one job, one good name (a verb: calculate_tax, send_email).",
        career_hack="When a coding question looks big, say 'I will break this into three functions' and name them. It shows structured thinking.",
        recall=[dict(q="What is decomposition?", a="Breaking a big problem into smaller parts that each do one job."),
                dict(q="What is the difference between a parameter and a return value?", a="A parameter is input given to the function; the return value is the result it gives back.")],
        video=dict(youtube_id="YSozY8AmTSY", title="Mastering Programming Part 1: Decomposing Simple Tasks",
                   channel="Kingsley Atuba", minutes=4, checked_on="2026-11-06",
                   why="Breaks three small Python tasks (sum, maximum and average of a list) into separate input, processing and output functions.")),
    "pf-i1": dict(
        from_zero="A doctor does not guess a medicine. They ask when the pain started, test one thing at a time and check that the "
                  "treatment worked. Debugging is the same: reproduce the problem, narrow down where it happens, fix it, then prove it is fixed.",
        memory_trick="R-N-F-P: Reproduce, Narrow down, Fix, Prove (with a test).",
        career_hack="When you are asked about a hard bug you fixed, describe these four steps and the test you added so it never came back.",
        recall=[dict(q="What is the first step when you meet a bug?", a="Make it happen again reliably (reproduce it) with the smallest possible input."),
                dict(q="How do you prove a bug is fixed?", a="Write a test that failed before the fix and passes after it.")],
        video=dict(youtube_id="7qZBwhSlfOo", title="How to Use a Debugger - Debugger Tutorial",
                   channel="Tech With Tim", minutes=17, checked_on="2026-11-06",
                   why="Explains what debugging is and how to use a debugger in VS Code, with concepts that apply to all debuggers.")),
    "pf-a1": dict(
        from_zero="Imagine writing a note for a friend who will cook your dinner next week. If it says 'do the thing with the stuff', "
                  "they cannot follow it. Clean code is a clear note for the next developer, who may be you in six months.",
        memory_trick="Name it, shrink it, don't repeat it: clear names, small functions, no copy-paste (DRY).",
        career_hack="In code reviews, explain why a change is clearer (better name, smaller function, removed duplication), not only that it is.",
        recall=[dict(q="Why is clear code important if the program already works?", a="Code is read and changed far more often than it is written; unclear code causes bugs and slows the team."),
                dict(q="What does DRY mean?", a="Don't Repeat Yourself: put repeated logic in one place, such as a function.")],
        video=dict(youtube_id="KRDoN-ZkDdk", title="5 Easy Principles for ALWAYS Writing Clean Code",
                   channel="Mark Inman", minutes=7, checked_on="2026-11-06",
                   why="Shows five easy clean-code principles with short do-and-don't examples in C#; the ideas apply to most languages.")),

    # ------------------------------------------------------------------ Python (SK002)
    "py-b1": dict(
        from_zero="A variable is like a label on a box. The label is the name (price); the box holds a value (450). The kind of value "
                  "(number, text, true/false) decides what you can do: you can add two numbers, but '450' + 50 fails because one is text.",
        memory_trick="Name → value → type. Ask 'what type is this?' whenever Python gives a TypeError.",
        career_hack="Know the difference between int, float, str and bool and how to convert them (int('42')). It is a common warm-up question.",
        recall=[dict(q="What does type(3.5) return?", a="float."),
                dict(q="Why does '5' + 3 fail in Python?", a="You cannot add text (str) and a number (int); convert one first, e.g. int('5') + 3.")],
        video=dict(youtube_id="LKFrQXaoSMQ", title="Python variables for beginners ❎",
                   channel="Bro Code", minutes=14, checked_on="2026-11-06",
                   why="Explains variables, f-strings and the four basic data types: integers, floats, strings and booleans.")),
    "py-b2": dict(
        from_zero="A list is like a numbered queue of people: order matters and you find someone by position. A dictionary is like a "
                  "phone book: you look up a name (key) to get a number (value). A for loop is 'do this for every person in the queue'.",
        memory_trick="List = [order]. Dict = {key: value}. Loop = 'for each item, do...'.",
        career_hack="Interviewers often ask you to count things (word counts, frequencies). The usual answer is a dictionary updated inside a loop.",
        recall=[dict(q="When do you use a dictionary instead of a list?", a="When you look things up by a key (name, ID) instead of by position."),
                dict(q="What does len(['a', 'b', 'c']) return?", a="3.")],
        video=dict(youtube_id="RQdpQHhc9oY", title="Python Lists and Dictionaries Explained | Python for Beginners #5",
                   channel="TechNut_CodingTutorials", minutes=11, checked_on="2026-11-06",
                   why="Covers creating, accessing, changing and looping through Python lists and dictionaries.")),
    "py-i1": dict(
        from_zero="A coffee machine is a function: you give it inputs (coffee, milk, size) and it returns a drink. You do not need to "
                  "know how it works inside to use it. A module is a shelf of such machines you can import into any kitchen.",
        memory_trick="def = define once, call many times. import = borrow someone else's functions.",
        career_hack="Mention default arguments and keyword arguments (send(email, retries=3)). They show you write flexible, readable APIs.",
        recall=[dict(q="What does a function return if it has no return statement?", a="None."),
                dict(q="Why put functions in a separate module?", a="To reuse them in many files and keep each file small and focused.")],
        video=dict(youtube_id="9Os0o3wzS_I", title="Python Tutorial for Beginners 8: Functions",
                   channel="Corey Schafer", minutes=22, checked_on="2026-11-06",
                   why="Shows how to define functions, pass in arguments and return values.")),
    "py-i2": dict(
        from_zero="When you post a parcel, the address may be wrong. A good post office has a plan: return it to the sender. "
                  "try/except is that plan in code: try the normal action and, if a known problem happens, handle it on purpose.",
        memory_trick="try the risky part, except the specific error, finally clean up. Use 'with open(...)' so files always close.",
        career_hack="Never write a bare 'except:'. Catch specific errors (FileNotFoundError, ValueError); interviewers notice this.",
        recall=[dict(q="Why use 'with open(...) as f' instead of open() alone?", a="It closes the file automatically, even if an error happens."),
                dict(q="Which exception does int('abc') raise?", a="ValueError.")],
        video=dict(youtube_id="H_8-dJGRZ6o", title="Python File Handling and Exceptions - Master the Basics",
                   channel="Code And Course", minutes=7, checked_on="2026-11-06",
                   why="Covers reading and writing files, plus best practices for handling errors and exceptions in Python.")),
    "py-a1": dict(
        from_zero="Before a plane takes off, pilots run a checklist every time. Tests are your program's checklist: small pieces of "
                  "code that check other code still works after every change.",
        memory_trick="A-A-A: Arrange the data, Act (call the code), Assert the result.",
        career_hack="Say that you add a test for every bug you fix. Teams value developers who prevent the same bug from returning.",
        recall=[dict(q="What are the three parts of a good test?", a="Arrange (set up), Act (run the code), Assert (check the result)."),
                dict(q="Why are automated tests useful when you change code?", a="They quickly show if a change broke something that used to work.")],
        video=dict(youtube_id="_0soBPejyu4", title="Introduction to Unit Tests in Python | Tutorial",
                   channel="StudyStream+", minutes=12, checked_on="2026-11-06",
                   why="Uses Python's built-in unittest module to test a simple function and introduces the Assume/Action/Assert test layout.")),

    # ------------------------------------------------------------------ SQL (SK010)
    "sql-b1": dict(
        from_zero="A database table is like a spreadsheet of students. A SQL query is a polite request to it: 'show me the name and "
                  "marks (SELECT) from the students sheet (FROM) only for Year 2 (WHERE), highest marks first (ORDER BY)'.",
        memory_trick="Some Funny Workers Order: SELECT, FROM, WHERE, ORDER BY - the order you write them.",
        career_hack="Read a query aloud as a sentence before running it. In interviews, explaining it this way shows you understand, not memorise.",
        recall=[dict(q="Which clause filters rows?", a="WHERE."),
                dict(q="How do you sort the highest value first?", a="ORDER BY column DESC.")],
        video=dict(youtube_id="a56ZAJRkAdo", title="SQL Basics | SELECT, FROM, WHERE, ORDER BY in SQL | SQL Tutorial for Beginners",
                   channel="the_dataholics", minutes=7, checked_on="2026-11-06",
                   why="Explains how SELECT, FROM, WHERE and ORDER BY work together to retrieve data from a table.")),
    "sql-b2": dict(
        from_zero="Imagine sorting exam papers into piles by class, then writing one summary per pile: how many papers, the average "
                  "mark. GROUP BY makes the piles; COUNT, AVG and SUM write the summaries. HAVING throws away piles you do not want.",
        memory_trick="WHERE filters rows before grouping; HAVING filters groups after grouping.",
        career_hack="'What is the difference between WHERE and HAVING?' is one of the most common SQL interview questions.",
        recall=[dict(q="What does GROUP BY do?", a="Puts rows with the same value into one group so an aggregate (COUNT, AVG...) gives one row per group."),
                dict(q="Can you use AVG(marks) inside WHERE?", a="No. Aggregates are filtered with HAVING, after GROUP BY.")],
        video=dict(youtube_id="WKe56SDr34o", title="GROUP BY and HAVING in MySQL | COUNT, SUM, AVG Aggregate Functions",
                   channel="Placed Elite", minutes=6, checked_on="2026-11-06",
                   why="Covers COUNT, SUM, AVG, MIN and MAX, then GROUP BY, HAVING, execution order and why an aggregate in WHERE is an error (MySQL).")),
    "sql-i1": dict(
        from_zero="A school keeps students in one register and marks in another, linked by student ID, so a name is not written "
                  "100 times. A JOIN puts the two registers side by side again by matching the ID.",
        memory_trick="INNER = only matches; LEFT = everything on the left, matches if they exist (else NULL).",
        career_hack="Draw two overlapping circles when you explain INNER vs LEFT JOIN. It is quick and interviewers like it.",
        recall=[dict(q="Which JOIN keeps students who have no marks?", a="LEFT JOIN from students to marks; their mark columns are NULL."),
                dict(q="What links two tables in a JOIN?", a="A matching key, usually a primary key in one table and a foreign key in the other.")],
        video=dict(youtube_id="j-_3ATJ98WY", title="All SQL Joins Explained in 10 Minutes: Inner, Left, Right, Full, Cross, and Self Joins. #sql",
                   channel="The Code Samples", minutes=10, checked_on="2026-11-06",
                   why="Explains why joins are needed and how inner, left, right, full, cross and self joins work, using simple examples.")),
    "sql-i2": dict(
        from_zero="To find 'students above the class average', you first work out the average, then compare each student with it. "
                  "A subquery or a CTE (WITH ... AS) is that first step, given a name so the main query can use it.",
        memory_trick="WITH step1 AS (...), step2 AS (...) SELECT ... - build the answer one named step at a time.",
        career_hack="For long queries, say 'I will use a CTE to keep it readable'. Readability is part of how SQL is judged at work.",
        recall=[dict(q="What is a CTE?", a="A named temporary result defined with WITH ... AS, used by the query that follows."),
                dict(q="Why use a CTE instead of a deeply nested subquery?", a="It is easier to read, test step by step and reuse in the same query.")],
        video=dict(youtube_id="LJC8277LONg", title="SQL WITH Clause | Clearly Explained | CTEs vs Subqueries vs Temp Tables | Recursive CTEs",
                   channel="Maven Analytics", minutes=13, checked_on="2026-11-06",
                   why="Explains the WITH clause, compares CTEs with subqueries and temporary tables, and introduces recursive CTEs.")),
    "sql-a1": dict(
        from_zero="In a race, you want each runner's time and their rank. GROUP BY would squash runners into one row; a window "
                  "function looks at the other runners (the window) but still keeps one row per runner, adding the rank beside it.",
        memory_trick="OVER(PARTITION BY group ORDER BY value): split into groups, order inside each, keep every row.",
        career_hack="'Top 3 per category' and 'running total' are classic window-function interview tasks (ROW_NUMBER, SUM OVER).",
        recall=[dict(q="How is a window function different from GROUP BY?", a="It keeps every row and adds the calculated value to each one."),
                dict(q="Which function numbers rows 1, 2, 3 within each group?", a="ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ...).")],
        video=dict(youtube_id="j4Sa6UxHMtg", title="SQL Window Functions | ROW_NUMBER() | For Beginners | Data Analysis, Data Science, & Engineering",
                   channel="Stacey Samoe | Data, Strategy & Life", minutes=17, checked_on="2026-11-06",
                   why="Teaches the ROW_NUMBER() window function with PARTITION BY, at beginner level.")),

    # ------------------------------------------------------------------ Git (SK014)
    "git-b1": dict(
        from_zero="Imagine saving a game. Each save point lets you go back if something goes wrong. A commit is a save point for "
                  "your project; the staging area is where you choose which changes go into that save.",
        memory_trick="add = put in the box, commit = seal and label the box, status = look at the boxes.",
        career_hack="Good commit messages ('Fix crash when list is empty') are noticed in team work and code reviews. Avoid 'update'.",
        recall=[dict(q="What does git add do?", a="Stages a change so it is included in the next commit."),
                dict(q="Which file tells Git to ignore secrets and generated files?", a=".gitignore.")],
        video=dict(youtube_id="KngvG8WzYLU", title="Git & GitHub Tutorial for Beginners #5 - Staging files",
                   channel="Net Ninja", minutes=6, checked_on="2026-11-06",
                   why="Introduces the staging area, where files are added before they are committed.")),
    "git-b2": dict(
        from_zero="You want to repaint your room but are not sure about the colour. You test it on a spare board first. A branch is "
                  "that spare board: you try a feature there, and only when it looks good do you bring it into the main room (merge).",
        memory_trick="switch -c to start, commit to work, switch main + merge to finish, branch -d to tidy up.",
        career_hack="Explain that you never commit directly to main and use one short-lived branch per feature or ticket.",
        recall=[dict(q="Which branch receives the changes when you run git merge feature?", a="The branch you are currently on."),
                dict(q="What is a fast-forward merge?", a="When main has no new commits, Git just moves main forward to the feature branch's commit.")],
        video=dict(youtube_id="7YovOpvO3S0", title="Git Branching and Merging Tutorial for Beginners: Create, Switch & Merge",
                   channel="freeplacementcourse ", minutes=12, checked_on="2026-11-06",
                   why="Shows how to create branches, switch between them safely and merge changes back into the master branch.")),
    "git-i1": dict(
        from_zero="A shared Google Doc is the remote: everyone's copy syncs with it. A pull request is like 'suggesting mode': you "
                  "propose changes and a teammate reviews them before they become part of the real document.",
        memory_trick="pull before you push. Conflict = Git asks you to choose; you edit, add, commit.",
        career_hack="Describe a merge conflict you solved and how you checked the result (ran the tests). It shows real team experience.",
        recall=[dict(q="What is a pull request for?", a="Asking teammates to review your branch before it is merged."),
                dict(q="What do you do after editing a file to resolve a conflict?", a="git add the file, then commit (or continue the merge/rebase).")],
        video=dict(youtube_id="oFYyTZwMyAg", title="GITHUB PULL REQUEST, Branching, Merging & Team Workflow",
                   channel="LearnCode.academy", minutes=11, checked_on="2026-11-06",
                   why="Walks through a team workflow: a feature branch, merge conflicts, submitting and discussing a pull request, then merging it.")),
    "git-a1": dict(
        from_zero="Crossing out a mistake in a shared notebook keeps the history honest (revert). Tearing out the page changes "
                  "history (reset, rebase) - fine in your private notebook, but confusing in one that others already copied.",
        memory_trick="Shared branch? revert. Your own branch? reset or rebase is fine.",
        career_hack="Knowing when not to force-push to a shared branch is a sign of a careful team member.",
        recall=[dict(q="Which command undoes a commit by adding a new commit?", a="git revert."),
                dict(q="Why is rewriting history on a shared branch risky?", a="Teammates already have the old commits, so their history no longer matches.")],
        video=dict(youtube_id="GytsxgB4-HU", title="Undo a git commit - git reset/revert - pushed/not pushed",
                   channel="Philomatics", minutes=3, checked_on="2026-11-06",
                   why="Shows how to undo a git commit, pushed or not pushed, using git reset and git revert.")),

    # ------------------------------------------------------------------ OOP (SK008)
    "oop-b1": dict(
        from_zero="A cookie cutter is a class; each cookie is an object. All cookies have the same shape (attributes and methods), "
                  "but each can have different decoration (its own data).",
        memory_trick="Class = blueprint, object = the thing built from it, self = 'this particular one'.",
        career_hack="Model a real thing in an interview (BankAccount with deposit and withdraw). Interviewers often ask this.",
        recall=[dict(q="What is the difference between a class and an object?", a="A class is the blueprint; an object is one instance created from it."),
                dict(q="What does __init__ do in Python?", a="It sets up a new object's starting data when the object is created.")],
        video=dict(youtube_id="ZDa-Z5JzLYM", title="Python OOP Tutorial 1: Classes and Instances",
                   channel="Corey Schafer", minutes=15, checked_on="2026-11-06",
                   why="Shows how to create and use classes and instances in Python to group data and functions.")),
    "oop-i1": dict(
        from_zero="A car's engine is hidden under the bonnet; you use the steering wheel and pedals (encapsulation). A sports car "
                  "is still a car, with extra features (inheritance): it reuses what a car has and adds more.",
        memory_trick="Encapsulation = hide and protect. Inheritance = 'is a' (a SavingsAccount is an Account).",
        career_hack="Say you prefer methods such as withdraw() over changing balance directly, because the method can check the rules.",
        recall=[dict(q="What does encapsulation protect?", a="An object's data, by letting other code change it only through its methods."),
                dict(q="Which relationship does inheritance describe?", a="'is a': the child class is a kind of the parent class.")],
        video=dict(youtube_id="pTB0EiLXUC8", title="Object-Oriented Programming, Simplified",
                   channel="Programming with Mosh", minutes=8, checked_on="2026-11-06",
                   why="Explains the four pillars of object-oriented programming, including encapsulation and inheritance.")),
    "oop-i2": dict(
        from_zero="Say 'speak' to a dog and a cat: the dog barks, the cat meows. You used one instruction, and each animal answered "
                  "in its own way. That is polymorphism. Abstraction means you only need to know 'it can speak', not how.",
        memory_trick="Same call, different behaviour. Program to the 'what', not the 'how'.",
        career_hack="Payment examples (card, cash, wallet all have pay()) are a clear way to explain polymorphism in interviews.",
        recall=[dict(q="What is polymorphism?", a="Different objects respond to the same method call in their own way."),
                dict(q="What is an abstract class for?", a="To define methods every subclass must provide, without saying how.")],
        video=dict(youtube_id="Dz2jBQem-3Y", title="Abstraction, Polymorphism, and Encapsulation in Python | Object Oriented Programming in Python",
                   channel="JoanMedia", minutes=15, checked_on="2026-11-06",
                   why="Explores polymorphism, abstraction and encapsulation in Python, including how Python calls the right method for each object type.")),
    "oop-a1": dict(
        from_zero="A phone charger works with any socket of the right type because both follow a standard. Good designs work the "
                  "same way: small parts with clear jobs that connect through agreed interfaces, so you can swap one without breaking others.",
        memory_trick="SOLID: Single responsibility, Open/closed, Liskov, Interface segregation, Dependency inversion.",
        career_hack="'Prefer composition over inheritance' is a common design-interview point; give one example (a Car has an Engine).",
        recall=[dict(q="What does the Single Responsibility Principle say?", a="A class should have only one reason to change."),
                dict(q="What is composition?", a="Building a class from other objects it has (has-a), instead of inheriting from them.")],
        video=dict(youtube_id="5999cgzA95A", title="SOLID principles explained | Java |  System Design Interview",
                   channel="ByteMonk", minutes=11, checked_on="2026-11-06",
                   why="Explains the SOLID design principles for flexible, maintainable object-oriented code, starting with Single Responsibility and Open-Closed.")),

    # ------------------------------------------------------------------ DSA (SK009)
    "dsa-b1": dict(
        from_zero="Finding a name by reading every page of a phone book takes longer the bigger the book (O(n)). Opening a book "
                  "at a known page number takes the same time for any size (O(1)). Big-O describes this growth.",
        memory_trick="O(1) instant, O(log n) halving, O(n) look at each, O(n²) each with each.",
        career_hack="Always state the time and space complexity of your solution at the end of a coding interview.",
        recall=[dict(q="What is the time to read the item at a known index of an array?", a="O(1)."),
                dict(q="What does O(n) mean?", a="The time grows in proportion to the input size.")],
        video=dict(youtube_id="XMUe3zFhM5c", title="Learn Big O notation in 6 minutes 📈",
                   channel="Bro Code", minutes=6, checked_on="2026-11-06",
                   why="A short tutorial that explains Big O notation with examples.")),
    "dsa-b2": dict(
        from_zero="A stack is a pile of plates: you take the top one first (last in, first out). A queue is a line at the bank: "
                  "the first person to arrive is served first (first in, first out).",
        memory_trick="Stack = LIFO (plates). Queue = FIFO (bank line).",
        career_hack="Undo buttons and checking brackets use stacks; task scheduling and BFS use queues. Name a real use when asked.",
        recall=[dict(q="Which structure is LIFO?", a="A stack."),
                dict(q="Which structure would you use to process print jobs in arrival order?", a="A queue.")],
        video=dict(youtube_id="aBR8SxPMbng", title="Stacks & Queues | Data Structures",
                   channel="Giraffe Academy", minutes=10, checked_on="2026-11-06",
                   why="Introduces stacks and queues and their first-in-last-out and first-in-first-out ordering, with JavaScript implementations.")),
    "dsa-i1": dict(
        from_zero="A library gives every book a shelf number from its title, so you walk straight to the shelf instead of "
                  "checking every book. A hash function gives each key a 'shelf number', so lookups are usually instant.",
        memory_trick="Hash the key → jump to the bucket → usually O(1).",
        career_hack="Many interview problems (two-sum, duplicates, counting) become O(n) with a dictionary or set. Say this out loud.",
        recall=[dict(q="What is the usual time to find a key in a hash table?", a="O(1) on average."),
                dict(q="What is a collision?", a="When two different keys get the same position; the table must store both.")],
        video=dict(youtube_id="FsfRsGFHuv4", title="Learn Hash Tables in 13 minutes #️⃣",
                   channel="Bro Code", minutes=13, checked_on="2026-11-06",
                   why="Explains how a hash table stores unique keys and values for fast insertion, lookup and deletion.")),
    "dsa-i2": dict(
        from_zero="To find a word in a dictionary you open the middle, then go left or right and repeat. Each step halves the "
                  "pages left. That is binary search, and it only works because the dictionary is sorted.",
        memory_trick="Sorted? Then halve it: binary search is O(log n).",
        career_hack="Before using binary search, say 'this works because the data is sorted'. Interviewers check that you know the condition.",
        recall=[dict(q="What must be true before you can use binary search?", a="The data must be sorted."),
                dict(q="What is the time complexity of binary search?", a="O(log n).")],
        video=dict(youtube_id="A6sUupg8ylE", title="Binary Search, Selection Sort, Insertion Sort, Recursive Algorithms in C++",
                   channel="Simon Lee", minutes=12, checked_on="2026-11-06",
                   why="Explains binary search and its time complexity, plus selection sort and insertion sort, with C++ code.")),
    "dsa-a1": dict(
        from_zero="A city map is a graph: places are nodes and roads are edges. BFS is like ripples in water, visiting nearby places "
                  "first; DFS is like walking one road as far as it goes before coming back to try another.",
        memory_trick="BFS uses a Queue (wide, level by level). DFS uses a Stack or recursion (deep first).",
        career_hack="'Shortest path in an unweighted graph' means BFS. Recognising this pattern is often half the interview answer.",
        recall=[dict(q="Which traversal finds the shortest path in an unweighted graph?", a="Breadth-first search (BFS)."),
                dict(q="Which data structure does BFS use?", a="A queue.")],
        video=dict(youtube_id="kyUpc_5705s", title="BFS DFS - Simplified",
                   channel="Abdul Bari", minutes=19, checked_on="2026-11-06",
                   why="Explains breadth-first and depth-first search traversal of a graph, with valid and invalid examples.")),
}

# ---------------------------------------------------------------------------------------------- interactive exercises
# Practice exercises, 3 per topic, checked instantly on the server (tutor.check_exercise). They are PRACTICE ONLY: never
# evidence, never mastery, placement, roadmap or readiness. Drafted with an AI coding assistant from each topic's own
# explanation and worked example, for the C4 author to review.
#
# Fields: id, type, language, prompt, hint, explanation, plus
#   predict_output  code, options, answer (index)     - choose what the code prints (an error is shown by its type name)
#   fill_blank      code with one ____, answers       - accepted answers, compared after normalisation (tutor._norm_code);
#                   optional ignore_case (SQL keywords)
#   find_bug        lines, answer (index of the wrong line), fix (the corrected line, for runnable languages)
#   order_steps     lines in the CORRECT order (the student receives them shuffled)
#   setup           code that runs first (required for SQL: tables and rows); shown to the student
#   expected_output what the finished program prints (runnable fill_blank / find_bug / order_steps)
# Verification (tests/component04_roadmap/test_tutor.py): every python and sql exercise is run - the marked option
# must equal the real output; every accepted blank must produce expected_output; the fixed line must produce
# expected_output while the original does not; the correct order must produce expected_output and no other order may.
# SQL runs on an in-memory sqlite3 database; result rows are written as "value, value; value, value".
# bash and text exercises cannot be run safely in a test, so they are checked by structure only.

_SQL_CUSTOMERS = """CREATE TABLE customers (id INTEGER, name TEXT, city TEXT, status TEXT, joined_on TEXT);
INSERT INTO customers VALUES
  (1, 'Ama', 'Colombo', 'active', '2025-03-01'),
  (2, 'Ben', 'Kandy', 'active', '2025-06-10'),
  (3, 'Chen', 'Galle', 'inactive', '2024-11-20'),
  (4, 'Dev', 'Colombo', 'active', '2026-01-05'),
  (5, 'Esha', NULL, 'active', '2025-09-15');"""

_SQL_SALES = """CREATE TABLE orders (id INTEGER, category TEXT, amount INTEGER, order_date TEXT);
INSERT INTO orders VALUES
  (1, 'books', 1200, '2026-01-10'),
  (2, 'books', 800, '2026-02-02'),
  (3, 'games', 5000, '2026-02-15'),
  (4, 'music', 300, '2025-12-30'),
  (5, 'music', 700, '2026-03-01'),
  (6, 'books', 500, '2026-03-05');"""

_SQL_SHOP = """CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, amount INTEGER);
INSERT INTO customers VALUES (1, 'Ama'), (2, 'Ben'), (3, 'Chen');
INSERT INTO orders VALUES (10, 1, 500), (11, 1, 250), (12, 3, 900);"""

_SQL_PRODUCTS = """CREATE TABLE products (id INTEGER, name TEXT, category TEXT, price INTEGER);
INSERT INTO products VALUES
  (1, 'Pen', 'office', 100),
  (2, 'Desk', 'office', 9000),
  (3, 'Lamp', 'office', 2000),
  (4, 'Novel', 'books', 1500),
  (5, 'Atlas', 'books', 4500);"""

_SQL_WINDOWS = """CREATE TABLE orders (id INTEGER, customer TEXT, order_date TEXT, amount INTEGER);
INSERT INTO orders VALUES
  (1, 'Ama', '2026-01-05', 300),
  (2, 'Ama', '2026-02-10', 700),
  (3, 'Ben', '2026-01-20', 500),
  (4, 'Ama', '2026-03-01', 200),
  (5, 'Ben', '2026-02-25', 650);
CREATE TABLE scores (name TEXT, points INTEGER);
INSERT INTO scores VALUES ('Ama', 90), ('Ben', 85), ('Chen', 90), ('Dev', 80);"""

_PY_ACCOUNT = """class Account:
    def __init__(self, owner):
        self.owner = owner
        self.balance = 0

    def deposit(self, amount):
        self.balance += amount

    def withdraw(self, amount):
        if amount > self.balance:
            raise ValueError('Insufficient funds')
        self.balance -= amount"""

ROWS_NOTE = " Rows are separated by ';' and columns by ','."

EXERCISES = {
    # ------------------------------------------------------------------ Programming Fundamentals (SK001)
    "pf-b1": [
        dict(id="pf-b1-e1", type="predict_output", language="python", prompt="Trace the loop by hand. What does this print?",
             code="total = 0\nfor n in [3, 5, 2]:\n    total = total + n\nprint(total)",
             options=["5", "10", "2", "352"], answer=1,
             hint="Write down total after each pass of the loop: start at 0, then add 3, then 5, then 2.",
             explanation="total goes 0 -> 3 -> 8 -> 10. The loop adds every number once, so it prints 10."),
        dict(id="pf-b1-e2", type="fill_blank", language="python", prompt="Complete the condition so the program prints only the even numbers.",
             code="for n in range(1, 7):\n    if ____:\n        print(n, end=' ')", expected_output="2 4 6",
             answers=["n % 2 == 0", "n % 2 != 1", "not n % 2"],
             hint="A number is even when dividing it by 2 leaves no remainder. The % operator gives the remainder.",
             explanation="n % 2 is the remainder after dividing by 2; it is 0 for even numbers, so n % 2 == 0 keeps 2, 4 and 6."),
        dict(id="pf-b1-e3", type="find_bug", language="python",
             prompt="A mark of 50 or more is a pass. This prints 2, but three students passed. Which line is wrong?",
             lines=["marks = [72, 45, 88, 50]", "passed = 0", "for m in marks:", "    if m > 50:", "        passed = passed + 1", "print(passed)"],
             answer=3, fix="    if m >= 50:", expected_output="3",
             hint="Trace the mark 50. Is 50 > 50 true?",
             explanation="'50 or more' means >= 50. With > 50, the mark 50 is not counted, so the count is 2 instead of 3."),
    ],
    "pf-b2": [
        dict(id="pf-b2-e1", type="predict_output", language="python", prompt="Functions can use each other's results. What does this print?",
             code="def double(x):\n    return x * 2\n\ndef add_one(x):\n    return x + 1\n\nprint(add_one(double(4)))",
             options=["9", "10", "8", "5"], answer=0,
             hint="The inner call runs first: work out double(4), then pass that result to add_one.",
             explanation="double(4) returns 8, then add_one(8) returns 9."),
        dict(id="pf-b2-e2", type="fill_blank", language="python", prompt="Complete the function so it sends the average back to the caller.",
             code="def average(values):\n    ____ sum(values) / len(values)\n\nprint(average([2, 4, 9]))", expected_output="5.0",
             answers=["return"],
             hint="Which keyword ends a function and gives a value back?",
             explanation="return sends the result back to the caller; without it the function would give None."),
        dict(id="pf-b2-e3", type="order_steps", language="python",
             prompt="Decompose the task into steps and put them in order: get the marks, keep the passes, average them, show the result.",
             lines=["marks = [72, 45, 88]", "passed = [m for m in marks if m >= 50]", "average = sum(passed) / len(passed)", "print(average)"],
             expected_output="80.0",
             hint="Each step uses the value made by the step before it.",
             explanation="Each line needs the variable created by the line above it: marks -> passed -> average -> print. (72 + 88) / 2 = 80.0."),
    ],
    "pf-i1": [
        dict(id="pf-i1-e1", type="find_bug", language="python",
             prompt="count_words('find the bug') should return 3 but returns 1. There is no error message. Which line is wrong?",
             lines=["def count_words(text):", "    count = 0", "    for word in text.split():", "        count += 1",
                    "        return count", "print(count_words('find the bug'))"],
             answer=4, fix="    return count", expected_output="3",
             hint="This is a logic error. Look at the indentation: when does the function stop?",
             explanation="return is indented inside the loop, so the function stops after the first word. Move it out of the loop."),
        dict(id="pf-i1-e2", type="predict_output", language="python",
             prompt="Read the code like a traceback would. What happens when it runs? (An error is shown by its type.)",
             code="prices = {'tea': 120, 'coffee': 250}\nprint(prices['milk'])",
             options=["None", "KeyError", "0", "IndexError"], answer=1,
             hint="The key 'milk' is not in the dictionary. Which error does Python raise for a missing dictionary key?",
             explanation="Looking up a missing key with [] raises KeyError (the last line of the traceback says KeyError: 'milk'). "
                         "IndexError is for lists; .get('milk') would return None instead."),
        dict(id="pf-i1-e3", type="order_steps", language="text", prompt="Put the debugging steps in order (R-N-F-P).",
             lines=["Reproduce the bug with the smallest input that causes it",
                    "Narrow it down: test one hypothesis with a print or a breakpoint",
                    "Fix the cause you found",
                    "Prove it: rerun the failing case and add a test so the bug cannot return"],
             hint="Remember R-N-F-P: Reproduce, Narrow down, Fix, Prove.",
             explanation="You cannot narrow down a bug you cannot make happen, and you only know the fix worked when the failing case passes and a test guards it."),
    ],
    "pf-a1": [
        dict(id="pf-a1-e1", type="predict_output", language="python", prompt="This function uses guard clauses. What does it print?",
             code="def discount(total, member):\n    if total <= 0:\n        return 0\n    if not member:\n        return total\n    return total * 0.9\n\n"
                  "print(discount(200, False), discount(200, True))",
             options=["200 180.0", "0 180.0", "180.0 200", "200 200"], answer=0,
             hint="Check each guard in order for each call. Which return runs first?",
             explanation="For a non-member the second guard returns 200 unchanged. A member passes both guards and gets 200 * 0.9 = 180.0."),
        dict(id="pf-a1-e2", type="find_bug", language="python",
             prompt="A refactor to guard clauses broke this. A paid order with items should print 'ship', but it prints 'no items'. Which line is wrong?",
             lines=["def ship_status(order):", "    if not order['paid']:", "        return 'not paid'", "    if order['items']:",
                    "        return 'no items'", "    return 'ship'", "print(ship_status({'paid': True, 'items': ['book']}))"],
             answer=3, fix="    if not order['items']:", expected_output="ship",
             hint="A guard clause returns early for the bad case. What is the bad case for items?",
             explanation="The guard should reject orders with NO items (if not order['items']). Without 'not' it rejects every order that has items."),
        dict(id="pf-a1-e3", type="fill_blank", language="python",
             prompt="Don't repeat yourself: complete the line by reusing the vat() helper instead of copying the formula.",
             code="def vat(amount):\n    return round(amount * 0.18, 2)\n\nfood = 1000 + vat(1000)\nbooks = 500 + ____\nprint(food, books)",
             expected_output="1180.0 590.0", answers=["vat(500)"],
             hint="The food line already shows how to use the helper.",
             explanation="Calling vat(500) keeps the tax rule in one place; if the rate changes, only vat() changes."),
    ],

    # ------------------------------------------------------------------ Python (SK002)
    "py-b1": [
        dict(id="py-b1-e1", type="predict_output", language="python", prompt="What does this print?",
             code="print(7 // 2, 7 % 2, 7 / 2)", options=["3 1 3.5", "3.5 1 3", "3 1 3", "4 1 3.5"], answer=0,
             hint="// is whole-number division, % is the remainder and / always gives a float.",
             explanation="7 // 2 is 3, 7 % 2 is the remainder 1, and 7 / 2 is 3.5."),
        dict(id="py-b1-e2", type="find_bug", language="python",
             prompt="This should print 'Well done Ama, you scored 92' but it stops with a TypeError. Which line is wrong?",
             lines=["name = 'Ama'", "score = 92", "message = 'Well done ' + name + ', you scored ' + score", "print(message)"],
             answer=2, fix="message = 'Well done ' + name + ', you scored ' + str(score)",
             expected_output="Well done Ama, you scored 92",
             hint="What is the type of score? Can + join text and a number?",
             explanation="score is an int, and + cannot join a str and an int. Convert it with str(score) (or use an f-string)."),
        dict(id="py-b1-e3", type="fill_blank", language="python", prompt="year is text. Complete the line so the age is calculated as a number.",
             code="year = '2004'\nage = 2026 - ____\nprint(age)", expected_output="22", answers=["int(year)"],
             hint="Convert the text to a whole number before subtracting.",
             explanation="2026 - '2004' fails because one side is text. int(year) converts '2004' to 2004, giving 22."),
    ],
    "py-b2": [
        dict(id="py-b2-e1", type="predict_output", language="python", prompt="Lists are indexed from 0. What does this print?",
             code="names = ['Ama', 'Ben', 'Chen', 'Dev']\nprint(names[1], names[-1], len(names))",
             options=["Ben Dev 4", "Ama Dev 4", "Ben Chen 4", "Ama Dev 3"], answer=0,
             hint="Index 0 is the first item; index -1 is the last item.",
             explanation="names[1] is the second item 'Ben', names[-1] is the last item 'Dev', and the list has 4 items."),
        dict(id="py-b2-e2", type="fill_blank", language="python",
             prompt="Complete the counting pattern so a fruit seen for the first time starts from 0.",
             code="counts = {}\nfor fruit in ['apple', 'pear', 'apple']:\n    counts[fruit] = ____ + 1\nprint(counts)",
             expected_output="{'apple': 2, 'pear': 1}", answers=["counts.get(fruit, 0)"],
             hint="A dictionary method returns a default value when the key is missing.",
             explanation="counts.get(fruit, 0) gives the current count, or 0 for a new fruit, so the first 'apple' becomes 1 and the second 2."),
        dict(id="py-b2-e3", type="find_bug", language="python",
             prompt="This should add up all four prices (3800) but prints 2600. Which line is wrong?",
             lines=["prices = [1200, 800, 1500, 300]", "total = 0", "for i in range(1, len(prices)):", "    total += prices[i]", "print(total)"],
             answer=2, fix="for i in range(len(prices)):", expected_output="3800",
             hint="Which index does the loop start from? Which price is missing from 2600?",
             explanation="range(1, ...) starts at index 1 and skips the first price (1200). range(len(prices)) starts at 0. "
                         "Even simpler: for p in prices: total += p."),
    ],
    "py-i1": [
        dict(id="py-i1-e1", type="predict_output", language="python", prompt="Watch the default value. What does this print?",
             code="def add(item, items=[]):\n    items.append(item)\n    return items\n\nadd('a')\nprint(add('b'))",
             options=["['b']", "['a', 'b']", "['a']", "None"], answer=1,
             hint="The default list is created once, when the function is defined, not on every call.",
             explanation="Both calls share the same default list, so 'a' from the first call is still there. Use items=None and create the list inside."),
        dict(id="py-i1-e2", type="fill_blank", language="python", prompt="Complete the call so the greeting is 'Hi' instead of the default.",
             code="def greet(name, greeting='Hello'):\n    return f'{greeting}, {name}!'\n\nprint(greet('Ama', ____))",
             expected_output="Hi, Ama!", answers=["greeting='Hi'", "'Hi'"],
             hint="You can pass the value by position or, more clearly, by its parameter name.",
             explanation="greeting='Hi' (a keyword argument) replaces the default 'Hello'. Passing 'Hi' by position also works."),
        dict(id="py-i1-e3", type="find_bug", language="python",
             prompt="result should hold 'Pass', but the program prints 'Pass' and then None. Which line is wrong?",
             lines=["def grade(mark):", "    if mark >= 50:", "        print('Pass')", "    else:", "        return 'Fail'",
                    "result = grade(72)", "print(result)"],
             answer=2, fix="        return 'Pass'", expected_output="Pass",
             hint="A function that only prints gives nothing back to the caller.",
             explanation="print shows text but the function then returns None. return 'Pass' sends the value back, so result is 'Pass'."),
    ],
    "py-i2": [
        dict(id="py-i2-e1", type="predict_output", language="python", prompt="Follow try / except / finally. What does this print?",
             code="try:\n    value = int('12a')\n    print('number', end=' ')\nexcept ValueError:\n    print('not a number', end=' ')\n"
                  "finally:\n    print('done')",
             options=["number done", "not a number done", "not a number", "ValueError"], answer=1,
             hint="int('12a') fails on the first line of the try block. Does finally run after an error?",
             explanation="int('12a') raises ValueError, so the rest of the try block is skipped and except runs. finally always runs."),
        dict(id="py-i2-e2", type="fill_blank", language="python", prompt="Catch the specific error that int() raises for text that is not a number.",
             code="def safe_int(text):\n    try:\n        return int(text)\n    except ____:\n        return None\n\n"
                  "print(safe_int('42'), safe_int('abc'))",
             expected_output="42 None", answers=["ValueError", "(ValueError, TypeError)", "(TypeError, ValueError)"],
             hint="Try int('abc') in your head: which exception type does it raise?",
             explanation="int('abc') raises ValueError. Catching that specific error (not a bare except or Exception) keeps real bugs visible."),
        dict(id="py-i2-e3", type="order_steps", language="python",
             prompt="Put the lines in order so parse() returns the number, or None for bad text.",
             lines=["def parse(text):", "    try:", "        number = float(text)", "    except ValueError:", "        return None",
                    "    return number", "print(parse('3.5'), parse('x'))"],
             expected_output="3.5 None",
             hint="Keep the try block small: only the risky conversion goes inside it.",
             explanation="Only float(text) can fail, so it is the only line in try. except handles the bad text, and the "
                         "normal return comes after the try/except."),
    ],
    "py-a1": [
        dict(id="py-a1-e1", type="predict_output", language="python",
             prompt="This runs one boundary test in code. Does the test pass? What does it print?",
             code="import unittest\n\ndef grade(mark):\n    return 'Pass' if mark > 50 else 'Fail'\n\n"
                  "class GradeTests(unittest.TestCase):\n    def test_pass_at_boundary(self):\n        self.assertEqual(grade(50), 'Pass')\n\n"
                  "result = unittest.TestResult()\nunittest.TestLoader().loadTestsFromTestCase(GradeTests).run(result)\nprint(result.wasSuccessful())",
             options=["True", "False", "None", "AssertionError"], answer=1,
             hint="What does grade(50) return when the rule is mark > 50?",
             explanation="grade(50) returns 'Fail' because 50 > 50 is false, so assertEqual fails and wasSuccessful() is False. "
                         "This is why boundary tests matter: they catch > vs >= bugs."),
        dict(id="py-a1-e2", type="fill_blank", language="python", prompt="Complete the test so it checks that dividing by zero raises ValueError.",
             code="import unittest\n\ndef safe_divide(a, b):\n    if b == 0:\n        raise ValueError('b must not be 0')\n    return a / b\n\n"
                  "class DivideTests(unittest.TestCase):\n    def test_zero(self):\n        with self.____(ValueError):\n            safe_divide(1, 0)\n\n"
                  "result = unittest.TestResult()\nunittest.TestLoader().loadTestsFromTestCase(DivideTests).run(result)\nprint(result.wasSuccessful())",
             expected_output="True", answers=["assertRaises"],
             hint="Which assert method is used with 'with' to expect an error?",
             explanation="with self.assertRaises(ValueError): passes only if the block raises ValueError."),
        dict(id="py-a1-e3", type="order_steps", language="python", prompt="Arrange the test in Arrange-Act-Assert order.",
             lines=["def test_total():", "    cart = [120, 80]", "    total = sum(cart)", "    return total == 200", "print(test_total())"],
             expected_output="True",
             hint="Arrange the data, Act (call the code), Assert the result.",
             explanation="Arrange creates cart, Act computes total, Assert compares it with 200. Each step needs the one before it."),
    ],

    # ------------------------------------------------------------------ SQL (SK010)
    "sql-b1": [
        dict(id="sql-b1-e1", type="predict_output", language="sql", setup=_SQL_CUSTOMERS,
             prompt="Which names does this query return, in order?" + ROWS_NOTE,
             code="SELECT name FROM customers\nWHERE city = 'Colombo' AND status = 'active'\nORDER BY joined_on DESC;",
             options=["Dev; Ama", "Ama; Dev", "Ama; Dev; Esha", "Dev"], answer=0,
             hint="First keep the rows that match both conditions, then sort the newest join date first.",
             explanation="Ama and Dev are the active customers in Colombo. DESC puts the latest joined_on first: Dev (2026) then Ama (2025)."),
        dict(id="sql-b1-e2", type="fill_blank", language="sql", setup=_SQL_CUSTOMERS, ignore_case=True,
             prompt="Complete the WHERE clause to find the customer whose city is unknown.",
             code="SELECT name FROM customers WHERE city ____;", expected_output="Esha", answers=["IS NULL"],
             hint="NULL means unknown, so = NULL never matches. Which two words test for NULL?",
             explanation="city IS NULL matches rows with no city. city = NULL is never true, so it would return nothing."),
        dict(id="sql-b1-e3", type="find_bug", language="sql", setup=_SQL_CUSTOMERS,
             prompt="This should list ACTIVE customers in Galle or Kandy, but it also returns Chen, who is inactive. Which line is wrong?",
             lines=["SELECT name, city", "FROM customers", "WHERE city = 'Galle' OR city = 'Kandy' AND status = 'active'", "ORDER BY name;"],
             answer=2, fix="WHERE (city = 'Galle' OR city = 'Kandy') AND status = 'active'", expected_output="Ben, Kandy",
             hint="AND is applied before OR. Which conditions does AND join here?",
             explanation="Without parentheses it means Galle OR (Kandy AND active), so inactive Chen in Galle matches. "
                         "Put parentheses around the OR (or use city IN ('Galle', 'Kandy'))."),
    ],
    "sql-b2": [
        dict(id="sql-b2-e1", type="predict_output", language="sql", setup=_SQL_SALES,
             prompt="What does this query return?" + ROWS_NOTE,
             code="SELECT category, COUNT(*) FROM orders\nGROUP BY category\nORDER BY category;",
             options=["books, 3; games, 1; music, 2", "books, 2500; games, 5000; music, 1000", "books, 3; music, 2", "6"], answer=0,
             hint="GROUP BY makes one row per category; COUNT(*) counts the rows in each group.",
             explanation="There are 3 books orders, 1 games order and 2 music orders. COUNT counts rows; SUM(amount) would give the totals."),
        dict(id="sql-b2-e2", type="fill_blank", language="sql", setup=_SQL_SALES, ignore_case=True,
             prompt="Keep only the categories whose revenue is more than 2000.",
             code="SELECT category, SUM(amount) AS revenue\nFROM orders\nGROUP BY category\n____ SUM(amount) > 2000\nORDER BY revenue DESC;",
             expected_output="games, 5000; books, 2500", answers=["HAVING"],
             hint="This filter uses an aggregate and comes after GROUP BY.",
             explanation="HAVING filters groups after aggregation. WHERE runs before grouping and cannot use SUM()."),
        dict(id="sql-b2-e3", type="find_bug", language="sql", setup=_SQL_SALES,
             prompt="This should show categories with more than one order, but the database reports an error. Which line is wrong?",
             lines=["SELECT category, COUNT(*) AS orders", "FROM orders", "GROUP BY category", "WHERE COUNT(*) > 1", "ORDER BY category;"],
             answer=3, fix="HAVING COUNT(*) > 1", expected_output="books, 3; music, 2",
             hint="Which clause filters groups after GROUP BY?",
             explanation="WHERE cannot come after GROUP BY and cannot use an aggregate. HAVING COUNT(*) > 1 filters the groups."),
    ],
    "sql-i1": [
        dict(id="sql-i1-e1", type="predict_output", language="sql", setup=_SQL_SHOP,
             prompt="What does this query return?" + ROWS_NOTE,
             code="SELECT c.name, COUNT(o.id) AS orders\nFROM customers AS c\nLEFT JOIN orders AS o ON o.customer_id = c.id\n"
                  "GROUP BY c.id, c.name\nORDER BY c.name;",
             options=["Ama, 2; Ben, 0; Chen, 1", "Ama, 2; Chen, 1", "Ama, 2; Ben, 1; Chen, 1", "Ama, 1; Ben, 1; Chen, 1"], answer=0,
             hint="LEFT JOIN keeps every customer. COUNT(o.id) skips NULLs.",
             explanation="Ben has no orders: LEFT JOIN keeps him with NULL order columns, and COUNT(o.id) counts 0 for him. "
                         "COUNT(*) would wrongly count 1."),
        dict(id="sql-i1-e2", type="fill_blank", language="sql", setup=_SQL_SHOP, ignore_case=True,
             prompt="Complete the join to find customers who have no orders.",
             code="SELECT c.name\nFROM customers AS c\n____ JOIN orders AS o ON o.customer_id = c.id\nWHERE o.id IS NULL;",
             expected_output="Ben", answers=["LEFT", "LEFT OUTER"],
             hint="You need every customer, even those with no matching order.",
             explanation="LEFT JOIN keeps all customers and fills NULL where there is no order; WHERE o.id IS NULL keeps only those."),
        dict(id="sql-i1-e3", type="find_bug", language="sql", setup=_SQL_SHOP,
             prompt="This should list each order with its customer's name, but it returns no rows. Which line is wrong?",
             lines=["SELECT c.name, o.amount", "FROM customers AS c", "INNER JOIN orders AS o ON o.id = c.id", "ORDER BY o.amount;"],
             answer=2, fix="INNER JOIN orders AS o ON o.customer_id = c.id", expected_output="Ama, 250; Ama, 500; Chen, 900",
             hint="Which column of orders points to the customer?",
             explanation="Join on the key that links the tables: orders.customer_id = customers.id. o.id is the order's own ID."),
    ],
    "sql-i2": [
        dict(id="sql-i2-e1", type="predict_output", language="sql", setup=_SQL_PRODUCTS,
             prompt="The average price is 3420. Which products does this return?" + ROWS_NOTE,
             code="SELECT name FROM products\nWHERE price > (SELECT AVG(price) FROM products)\nORDER BY price;",
             options=["Atlas; Desk", "Desk", "Lamp; Atlas; Desk", "Pen; Novel; Lamp"], answer=0,
             hint="The subquery runs first and gives one value. Which prices are above it?",
             explanation="The subquery returns 3420. Atlas (4500) and Desk (9000) are higher, cheapest first."),
        dict(id="sql-i2-e2", type="fill_blank", language="sql", setup=_SQL_PRODUCTS, ignore_case=True,
             prompt="Name the first step as a CTE called cheap.",
             code="____ cheap AS (\n  SELECT name, price FROM products WHERE price < 2000\n)\nSELECT COUNT(*) FROM cheap;",
             expected_output="2", answers=["WITH"],
             hint="A CTE starts with one keyword before its name.",
             explanation="WITH cheap AS (...) names the step; the main query then reads from cheap. Pen and Novel cost less than 2000."),
        dict(id="sql-i2-e3", type="order_steps", language="sql", setup=_SQL_PRODUCTS,
             prompt="Put the lines in order: a CTE with the office products, then their names, most expensive first.",
             lines=["WITH office AS (", "  SELECT name, price FROM products WHERE category = 'office'", ")", "SELECT name", "FROM office",
                    "ORDER BY price DESC;"],
             expected_output="Desk; Lamp; Pen",
             hint="The named step comes first; the main query that uses it comes after.",
             explanation="WITH ... AS ( ... ) defines the step at the top; then SELECT, FROM office and ORDER BY in the normal clause order."),
    ],
    "sql-a1": [
        dict(id="sql-a1-e1", type="predict_output", language="sql", setup=_SQL_WINDOWS,
             prompt="Ama and Chen both have 90 points. What does RANK() give?" + ROWS_NOTE,
             code="SELECT name, RANK() OVER (ORDER BY points DESC) AS r\nFROM scores\nORDER BY r, name;",
             options=["Ama, 1; Chen, 1; Ben, 3; Dev, 4", "Ama, 1; Chen, 1; Ben, 2; Dev, 3", "Ama, 1; Chen, 2; Ben, 3; Dev, 4",
                      "Ama, 1; Ben, 2; Chen, 3; Dev, 4"], answer=0,
             hint="RANK gives ties the same rank and then leaves a gap.",
             explanation="The two 90s share rank 1, so the next rank is 3 (a gap). DENSE_RANK would give Ben 2 and Dev 3."),
        dict(id="sql-a1-e2", type="fill_blank", language="sql", setup=_SQL_WINDOWS, ignore_case=True,
             prompt="Number each customer's orders separately, starting from 1 for every customer.",
             code="SELECT customer, ROW_NUMBER() OVER (____ customer ORDER BY order_date) AS n\nFROM orders\nORDER BY customer, n;",
             expected_output="Ama, 1; Ama, 2; Ama, 3; Ben, 1; Ben, 2", answers=["PARTITION BY"],
             hint="Which two words split the rows into one window per customer?",
             explanation="PARTITION BY customer restarts the numbering for each customer; without it the orders would be numbered 1-5 together."),
        dict(id="sql-a1-e3", type="find_bug", language="sql", setup=_SQL_WINDOWS,
             prompt="This should return each customer's LATEST order, but it returns the earliest. Which line is wrong?",
             lines=["WITH ranked AS (",
                    "  SELECT customer, amount, ROW_NUMBER() OVER (PARTITION BY customer ORDER BY order_date ASC) AS rn",
                    "  FROM orders", ")", "SELECT customer, amount FROM ranked WHERE rn = 1", "ORDER BY customer;"],
             answer=1, fix="  SELECT customer, amount, ROW_NUMBER() OVER (PARTITION BY customer ORDER BY order_date DESC) AS rn",
             expected_output="Ama, 200; Ben, 650",
             hint="rn = 1 is the first row in each window. Which order puts the latest date first?",
             explanation="With ASC, row 1 is the oldest order. ORDER BY order_date DESC makes row 1 the latest."),
    ],

    # ------------------------------------------------------------------ Git (SK014): not run in tests (structure only)
    "git-b1": [
        dict(id="git-b1-e1", type="predict_output", language="bash",
             prompt="You changed app.py and staged it. Under which heading does git status list app.py?",
             code="git add app.py\ngit status",
             options=["Changes to be committed", "Changes not staged for commit", "Untracked files", "nothing to commit, working tree clean"],
             answer=0,
             hint="git add moves a change into the staging area.",
             explanation="After git add, the change is staged, and git status lists it under 'Changes to be committed'."),
        dict(id="git-b1-e2", type="order_steps", language="bash", prompt="Put the commands in order to start a repository and save a first snapshot.",
             lines=["git init", "git add app.py", "git commit -m \"Add average calculation\"", "git log --oneline"],
             hint="Create the repository, choose the change, save the snapshot, then look at the history.",
             explanation="git init creates the repository, git add stages the file, git commit saves the snapshot, git log shows it."),
        dict(id="git-b1-e3", type="fill_blank", language="bash", prompt="Complete the command that saves the staged change with a message.",
             code="git add report.py\ngit ____ -m \"Fix average when list is empty\"", answers=["commit"],
             hint="Which command saves a snapshot of the staging area?",
             explanation="git commit -m \"message\" saves the staged changes as a new snapshot with a message that says what and why."),
    ],
    "git-b2": [
        dict(id="git-b2-e1", type="order_steps", language="bash", prompt="Put the feature-branch workflow in order.",
             lines=["git switch -c feature-login", "git add login.py", "git commit -m \"Add login form\"", "git switch main",
                    "git merge feature-login", "git branch -d feature-login"],
             hint="Work and commit on the branch, then go to the branch you merge into.",
             explanation="Create and switch to the branch, commit there, switch to main, merge the feature into main, then delete the finished branch."),
        dict(id="git-b2-e2", type="predict_output", language="bash",
             prompt="Nobody committed to main since you created feature-login. What does the merge do?",
             code="git switch main\ngit merge feature-login",
             options=["A fast-forward: main moves to the feature's latest commit", "It creates a merge commit with two parents",
                      "It deletes the feature branch", "It reports a merge conflict"], answer=0,
             hint="If main has no new commits, Git can simply move the main pointer forward.",
             explanation="When main did not change, Git fast-forwards. A merge commit is only needed when both branches have new commits."),
        dict(id="git-b2-e3", type="find_bug", language="bash", prompt="The goal is to merge fix-typo into main. Which is the first wrong line?",
             lines=["git switch -c fix-typo", "git add README.md", "git commit -m \"Fix typo in README\"", "git merge fix-typo",
                    "git branch -d fix-typo"],
             answer=3,
             hint="git merge brings a branch into the branch you are currently on. Which branch are you on at that line?",
             explanation="You are still on fix-typo, so this merges the branch into itself and main never gets the fix. "
                         "Run git switch main first, then git merge fix-typo. "
                         "The next line also fails, because Git cannot delete the branch you are on. "
                         "The fix is to add git switch main before the merge."),
    ],
    "git-i1": [
        dict(id="git-i1-e1", type="find_bug", language="text",
             prompt="This file was committed after a merge conflict was 'resolved'. Which line should not be there?",
             lines=["PASS_MARK = 40", "MAX_MARK = 100", ">>>>>>> feature-rules", "def grade(mark):"], answer=2,
             hint="Look for the markers Git adds to show a conflict.",
             explanation="The >>>>>>> line is a conflict marker. Remove all <<<<<<<, ======= and >>>>>>> markers before git add and commit."),
        dict(id="git-i1-e2", type="order_steps", language="text", prompt="Put the steps for resolving a merge conflict in order.",
             lines=["git pull --no-rebase origin main", "Edit rules.py: keep the correct lines and remove the conflict markers", "git add rules.py",
                    "git commit -m \"Merge main and resolve PASS_MARK conflict\"", "git push origin feature-rules"],
             hint="The conflict appears when you bring in teammates' commits; you push only after it is committed.",
             explanation="Pulling shows the conflict, you edit the file to the correct version, git add marks it resolved, commit finishes the merge, then push. "
                         "Plain git pull can stop with 'Need to specify how to reconcile divergent branches' when both "
                         "sides have new commits; --no-rebase tells Git to merge."),
        dict(id="git-i1-e3", type="predict_output", language="bash",
             prompt="A teammate pushed to main. You did not pull. What happens when you push?",
             code="git commit -m \"Update rules\"\ngit push origin main",
             options=["Git rejects the push because your branch is behind the remote", "Your commit replaces your teammate's commit",
                      "The server merges the two commits automatically", "The push succeeds with no message"], answer=0,
             hint="Git protects commits that are on the remote but not in your copy.",
             explanation="The push is rejected (non-fast-forward). Pull first, resolve any conflict, then push. Never force-push a shared branch."),
    ],
    "git-a1": [
        dict(id="git-a1-e1", type="predict_output", language="bash",
             prompt="You undo the last commit with a soft reset. What does git status show for that commit's changes?",
             code="git reset --soft HEAD~1\ngit status",
             options=["They are staged (Changes to be committed)", "They are deleted", "They are unstaged (Changes not staged for commit)",
                      "They are still in the commit"], answer=0,
             hint="--soft moves the branch pointer but keeps your changes in the staging area.",
             explanation="git reset --soft moves the branch back one commit and keeps its changes staged. --hard would delete them."),
        dict(id="git-a1-e2", type="fill_blank", language="bash",
             prompt="The bad commit is already on the shared main branch. Complete the safe undo that does not rewrite history.",
             code="git log --oneline\n# 9f8e7d6 Break the checkout page   (already pushed to main)\ngit ____ 9f8e7d6\ngit push",
             answers=["revert"],
             hint="Which command adds a new commit that undoes an old one?",
             explanation="git revert creates a new commit that undoes 9f8e7d6, so teammates' history is not rewritten. "
                         "Git opens an editor for the commit message: save and close it, or add --no-edit."),
        dict(id="git-a1-e3", type="find_bug", language="bash",
             prompt="Goal: undo the last commit on the shared main branch without rewriting history. Which is the first wrong line?",
             lines=["git switch main", "git pull", "git reset --hard HEAD~1", "git push --force"], answer=2,
             hint="Which commands rewrite history?",
             explanation="git reset --hard rewrites history (and deletes work), which then forces a force-push. Use git revert HEAD and a normal git push."),
    ],

    # ------------------------------------------------------------------ OOP (SK008)
    "oop-b1": [
        dict(id="oop-b1-e1", type="predict_output", language="python", prompt="Each object has its own data. What does this print?",
             code="class Counter:\n    def __init__(self):\n        self.value = 0\n\n    def add(self):\n        self.value += 1\n\n"
                  "a = Counter()\nb = Counter()\na.add()\na.add()\nb.add()\nprint(a.value, b.value)",
             options=["2 1", "3 3", "1 1", "2 2"], answer=0,
             hint="a and b are two separate objects. Count the add() calls on each one.",
             explanation="self.value belongs to each object: a was added to twice and b once."),
        dict(id="oop-b1-e2", type="order_steps", language="python", setup=_PY_ACCOUNT,
             prompt="Using the Account class shown, put the lines in order so it prints 'Ama 300'.",
             lines=["acc = Account('Ama')", "acc.deposit(500)", "acc.withdraw(200)", "print(acc.owner, acc.balance)"],
             expected_output="Ama 300",
             hint="An object must exist before you call its methods, and withdraw refuses more than the balance.",
             explanation="Create the object first, deposit before withdrawing (withdraw raises if the balance is too low), then print."),
        dict(id="oop-b1-e3", type="find_bug", language="python", prompt="This should print 'Hi, Ama' but raises a TypeError. Which line is wrong?",
             lines=["class Student:", "    def __init__(self, name):", "        self.name = name", "    def greet():",
                    "        return 'Hi, ' + self.name", "print(Student('Ama').greet())"],
             answer=3, fix="    def greet(self):", expected_output="Hi, Ama",
             hint="Every method receives the object as its first parameter.",
             explanation="greet() is missing self, so Python cannot pass the object in. def greet(self): fixes it."),
    ],
    "oop-i1": [
        dict(id="oop-i1-e1", type="predict_output", language="python", prompt="The balance is protected by a method. What does this print?",
             code="class Account:\n    def __init__(self):\n        self._balance = 100\n\n    @property\n    def balance(self):\n"
                  "        return self._balance\n\n    def withdraw(self, amount):\n        if amount > self._balance:\n"
                  "            return 'Insufficient funds'\n        self._balance -= amount\n        return self._balance\n\n"
                  "acc = Account()\nprint(acc.withdraw(150), acc.balance)",
             options=["Insufficient funds 100", "-50 -50", "Insufficient funds -50", "ValueError"], answer=0,
             hint="Does withdraw change _balance when the amount is too large?",
             explanation="withdraw checks the rule first and returns before changing _balance, so the balance stays 100. "
                         "That is encapsulation: the rule is always applied."),
        dict(id="oop-i1-e2", type="fill_blank", language="python", prompt="Complete the line so Dog reuses Animal's __init__.",
             code="class Animal:\n    def __init__(self, name):\n        self.name = name\n\nclass Dog(Animal):\n"
                  "    def __init__(self, name, breed):\n        ____.__init__(name)\n        self.breed = breed\n\n"
                  "d = Dog('Rex', 'beagle')\nprint(d.name, d.breed)",
             expected_output="Rex beagle", answers=["super()"],
             hint="Which built-in gives you the parent class's version of a method?",
             explanation="super().__init__(name) runs Animal's __init__, which sets self.name; Dog then adds breed."),
        dict(id="oop-i1-e3", type="find_bug", language="python",
             prompt="Student accounts should pay no fee, but this prints 100. Which line is wrong?",
             lines=["class Account:", "    def fee(self):", "        return 100", "class StudentAccount(Account):", "    def fees(self):",
                    "        return 0", "print(StudentAccount().fee())"],
             answer=4, fix="    def fee(self):", expected_output="0",
             hint="To override a method, the subclass must use exactly the same name.",
             explanation="fees is a new method, not an override, so fee() still comes from Account. Name it fee to override it."),
    ],
    "oop-i2": [
        dict(id="oop-i2-e1", type="predict_output", language="python",
             prompt="The loop calls the same method on different objects. What does this print?",
             code="class Card:\n    def pay(self, amount):\n        return f'card {amount}'\n\nclass Wallet:\n    def pay(self, amount):\n"
                  "        return f'wallet {amount}'\n\nfor method in [Wallet(), Card()]:\n    print(method.pay(10), end='; ')",
             options=["wallet 10; card 10;", "card 10; wallet 10;", "wallet 10;", "TypeError"], answer=0,
             hint="Each object answers pay() in its own way, in the order of the list.",
             explanation="Polymorphism: the loop calls pay() without checking the type; Wallet comes first in the list, then Card."),
        dict(id="oop-i2-e2", type="predict_output", language="python",
             prompt="Square forgot to implement the abstract method. What happens? (An error is shown by its type.)",
             code="from abc import ABC, abstractmethod\n\nclass Shape(ABC):\n    @abstractmethod\n    def area(self): ...\n\n"
                  "class Square(Shape):\n    def __init__(self, s):\n        self.s = s\n\nprint(Square(2).area())",
             options=["4", "None", "TypeError", "AttributeError"], answer=2,
             hint="Python checks abstract methods when you create the object.",
             explanation="A subclass that does not implement every abstract method cannot be instantiated: Square(2) raises TypeError."),
        dict(id="oop-i2-e3", type="fill_blank", language="python", prompt="Complete the line so one loop works for every shape.",
             code="class Circle:\n    def __init__(self, r): self.r = r\n    def area(self): return 3 * self.r ** 2\n\n"
                  "class Square:\n    def __init__(self, s): self.s = s\n    def area(self): return self.s ** 2\n\n"
                  "shapes = [Circle(1), Square(2)]\nprint(sum(s.____() for s in shapes))",
             expected_output="7", answers=["area"],
             hint="Both classes provide a method with the same name.",
             explanation="Both shapes have area(), so the loop calls s.area() without checking the type: 3 + 4 = 7."),
    ],
    "oop-a1": [
        dict(id="oop-a1-e1", type="predict_output", language="python",
             prompt="OrderService receives its notifier (dependency injection). What does the test print?",
             code="class FakeNotifier:\n    def __init__(self):\n        self.sent = []\n    def send(self, message):\n"
                  "        self.sent.append(message)\n\nclass OrderService:\n    def __init__(self, notifier):\n        self.notifier = notifier\n"
                  "    def place(self, order_id):\n        self.notifier.send(f'Order {order_id} placed')\n\n"
                  "fake = FakeNotifier()\nOrderService(fake).place(7)\nprint(fake.sent)",
             options=["['Order 7 placed']", "[]", "Order 7 placed", "None"], answer=0,
             hint="The service uses whatever notifier it was given.",
             explanation="The fake records the message instead of sending an email, so the test can check it: ['Order 7 placed']."),
        dict(id="oop-a1-e2", type="find_bug", language="python",
             prompt="Code written for any Bird should print 'flies, walks'. Which line breaks the Liskov substitution principle?",
             lines=["class Bird:", "    def move(self):", "        return 'flies'", "class Penguin(Bird):", "    def move(self):",
                    "        raise NotImplementedError('penguins cannot fly')", "print(', '.join(b.move() for b in [Bird(), Penguin()]))"],
             answer=5, fix="        return 'walks'", expected_output="flies, walks",
             hint="A subclass must work wherever its parent is expected.",
             explanation="Penguin.move() raises instead of moving, so code that works for Bird breaks for Penguin. It should return its own way of moving."),
        dict(id="oop-a1-e3", type="fill_blank", language="python", prompt="Car HAS an Engine (composition). Complete the line so the car uses it.",
             code="class Engine:\n    def start(self):\n        return 'engine started'\n\nclass Car:\n    def __init__(self, engine):\n"
                  "        self.engine = engine\n    def start(self):\n        return ____.start()\n\nprint(Car(Engine()).start())",
             expected_output="engine started", answers=["self.engine"],
             hint="The engine was stored on the object in __init__.",
             explanation="Car delegates to the Engine it holds (self.engine) instead of inheriting from Engine."),
    ],

    # ------------------------------------------------------------------ Data Structures and Algorithms (SK009)
    "dsa-b1": [
        dict(id="dsa-b1-e1", type="predict_output", language="python", prompt="Count the work done by a loop inside a loop. What does this print?",
             code="steps = 0\nn = 4\nfor i in range(n):\n    for j in range(n):\n        steps += 1\nprint(steps)",
             options=["4", "8", "16", "1"], answer=2,
             hint="The inner loop runs n times for each of the n outer passes.",
             explanation="4 x 4 = 16 steps. A loop inside a loop over the same data is O(n^2)."),
        dict(id="dsa-b1-e2", type="fill_blank", language="python", prompt="Make the lookup O(1): complete the line with the right empty structure.",
             code="def has_duplicate(items):\n    seen = ____\n    for x in items:\n        if x in seen:\n            return True\n"
                  "        seen.add(x)\n    return False\n\nprint(has_duplicate([3, 1, 4, 1]), has_duplicate([1, 2, 3]))",
             expected_output="True False", answers=["set()"],
             hint="The code calls seen.add(x), and 'x in ...' should be O(1) on average.",
             explanation="A set gives O(1) average lookups, so the whole function is O(n). Note {} is an empty dict, not a set."),
        dict(id="dsa-b1-e3", type="find_bug", language="python",
             prompt="has_duplicate_slow([1, 2, 3]) should be False, but it returns True. Which line is wrong?",
             lines=["def has_duplicate_slow(items):", "    for i in range(len(items)):", "        for j in range(i, len(items)):",
                    "            if items[i] == items[j]:", "                return True", "    return False",
                    "print(has_duplicate_slow([1, 2, 3]))"],
             answer=2, fix="        for j in range(i + 1, len(items)):", expected_output="False",
             hint="On the first pass, i and j are both 0. Which item is compared with which?",
             explanation="Starting j at i compares each item with itself. Start at i + 1 to compare each pair once."),
    ],
    "dsa-b2": [
        dict(id="dsa-b2-e1", type="predict_output", language="python", prompt="A stack serves the newest item first. What does this print?",
             code="stack = []\nfor item in ['a', 'b', 'c']:\n    stack.append(item)\nstack.pop()\nprint(stack.pop())",
             options=["a", "b", "c", "IndexError"], answer=1,
             hint="The first pop() removes 'c'. What is on top now?",
             explanation="LIFO: the first pop() removes 'c', the second removes and prints 'b'."),
        dict(id="dsa-b2-e2", type="predict_output", language="python", prompt="A queue serves the oldest item first. What does this print?",
             code="from collections import deque\nqueue = deque(['job1', 'job2'])\nqueue.append('job3')\nqueue.popleft()\nprint(queue.popleft())",
             options=["job1", "job2", "job3", "IndexError"], answer=1,
             hint="append adds at the back; popleft removes from the front.",
             explanation="FIFO: the first popleft() serves job1, the second serves job2."),
        dict(id="dsa-b2-e3", type="fill_blank", language="python", prompt="Complete the bracket checker: a ')' removes the matching '(' from the stack.",
             code="def balanced(text):\n    stack = []\n    for ch in text:\n        if ch == '(':\n            stack.append(ch)\n"
                  "        elif ch == ')':\n            if not stack:\n                return False\n            stack.____()\n    return not stack\n\n"
                  "print(balanced('(a(b))'), balanced('(()'))",
             expected_output="True False", answers=["pop"],
             hint="Which list method removes the top (last) item?",
             explanation="stack.pop() removes the most recent '('. The text is balanced when the stack is empty at the end."),
    ],
    "dsa-i1": [
        dict(id="dsa-i1-e1", type="predict_output", language="python", prompt="Dictionary keys must be hashable. What happens? (An error is shown by its type.)",
             code="prices = {}\nprices[['tea', 'large']] = 250\nprint(prices)",
             options=["{['tea', 'large']: 250}", "TypeError", "KeyError", "{}"], answer=1,
             hint="Lists can change, so they cannot be hashed.",
             explanation="A list is mutable and unhashable, so Python raises TypeError: unhashable type: 'list'. Use a tuple ('tea', 'large')."),
        dict(id="dsa-i1-e2", type="fill_blank", language="python", prompt="Complete the two-sum pattern: which value are we looking for?",
             code="def two_sum(nums, target):\n    seen = {}\n    for i, n in enumerate(nums):\n        need = ____\n        if need in seen:\n"
                  "            return seen[need], i\n        seen[n] = i\n    return None\n\nprint(two_sum([3, 5, 9, 1], 10))",
             expected_output="(2, 3)", answers=["target - n"],
             hint="n plus the number we need must equal target.",
             explanation="need = target - n is the complement. When it is already in seen, the two indexes add up to target: 9 + 1 = 10."),
        dict(id="dsa-i1-e3", type="order_steps", language="python",
             prompt="Put the lines in order so the function returns the first character that repeats, in O(n).",
             lines=["def first_repeat(text):", "    seen = set()", "    for ch in text:", "        if ch in seen:", "            return ch",
                    "        seen.add(ch)", "print(first_repeat('abcbad'))"],
             expected_output="b",
             hint="Check whether you have seen the character BEFORE you remember it.",
             explanation="Each character is checked against the set first and only then added, so 'b' is the first one found twice."),
    ],
    "dsa-i2": [
        dict(id="dsa-i2-e1", type="predict_output", language="python", prompt="Sort by mark (highest first), then by name for ties. What does this print?",
             code="students = [('Ama', 72), ('Ben', 88), ('Chen', 72)]\nranked = sorted(students, key=lambda s: (-s[1], s[0]))\n"
                  "print([name for name, mark in ranked])",
             options=["['Ben', 'Ama', 'Chen']", "['Ben', 'Chen', 'Ama']", "['Ama', 'Chen', 'Ben']", "['Ama', 'Ben', 'Chen']"], answer=0,
             hint="-s[1] puts the highest mark first; s[0] breaks the tie alphabetically.",
             explanation="Ben (88) first; Ama and Chen tie at 72 and are ordered by name."),
        dict(id="dsa-i2-e2", type="find_bug", language="python",
             prompt="binary_search should find 31 at index 4, but it returns -1. Which line is wrong?",
             lines=["def binary_search(items, target):", "    low, high = 0, len(items) - 1", "    while low < high:",
                    "        mid = (low + high) // 2", "        if items[mid] == target:", "            return mid",
                    "        if items[mid] < target:", "            low = mid + 1", "        else:", "            high = mid - 1",
                    "    return -1", "print(binary_search([3, 8, 12, 20, 31], 31))"],
             answer=2, fix="    while low <= high:", expected_output="4",
             hint="Trace it: when low and high both become 4, does the loop still check that item?",
             explanation="With low < high the loop stops when one item is left, so it is never checked. low <= high checks it."),
        dict(id="dsa-i2-e3", type="fill_blank", language="python",
             prompt="Use the bisect module to find where 60 would be inserted in the sorted list.",
             code="import bisect\nmarks = [40, 55, 70, 85]\nposition = bisect.____(marks, 60)\nprint(position)",
             expected_output="2", answers=["bisect_left", "bisect", "bisect_right"],
             hint="The module has a function with the same name as the module, plus _left and _right versions.",
             explanation="bisect_left (or bisect / bisect_right, since 60 is not in the list) returns 2, between 55 and 70, in O(log n)."),
    ],
    "dsa-a1": [
        dict(id="dsa-a1-e1", type="predict_output", language="python", prompt="This is BFS. In which order are the nodes visited?",
             code="from collections import deque\ngraph = {'A': ['B', 'C'], 'B': ['D'], 'C': ['E'], 'D': [], 'E': []}\n"
                  "order, queue, visited = [], deque(['A']), {'A'}\nwhile queue:\n    node = queue.popleft()\n    order.append(node)\n"
                  "    for nxt in graph[node]:\n        if nxt not in visited:\n            visited.add(nxt)\n            queue.append(nxt)\n"
                  "print(''.join(order))",
             options=["ABCDE", "ABDCE", "ACEBD", "AB"], answer=0,
             hint="A queue finishes one level before the next: A, then its neighbours, then theirs.",
             explanation="BFS goes level by level: A, then B and C, then D and E. ABDCE would be a depth-first order."),
        dict(id="dsa-a1-e2", type="fill_blank", language="python", prompt="Make this a depth-first search: complete the line that takes the next node.",
             code="graph = {'A': ['B', 'C'], 'B': ['D'], 'C': [], 'D': []}\nstack, visited, order = ['A'], set(), []\nwhile stack:\n"
                  "    node = stack.____()\n    if node in visited:\n        continue\n    visited.add(node)\n    order.append(node)\n"
                  "    stack.extend(reversed(graph[node]))\nprint(''.join(order))",
             expected_output="ABDC", answers=["pop"],
             hint="DFS uses a stack: take the most recently added item.",
             explanation="stack.pop() takes the newest node, so the search goes deep (A, B, D) before it comes back to C."),
        dict(id="dsa-a1-e3", type="find_bug", language="python",
             prompt="shortest_steps should return 2 (A -> B -> E), but it returns 3. Which line is wrong?",
             lines=["from collections import deque", "def shortest_steps(graph, start, goal):", "    queue = deque([(start, 0)])",
                    "    visited = {start}", "    while queue:", "        node, dist = queue.pop()", "        if node == goal:",
                    "            return dist", "        for nxt in graph[node]:", "            if nxt not in visited:",
                    "                visited.add(nxt)", "                queue.append((nxt, dist + 1))", "    return -1",
                    "g = {'A': ['B', 'C'], 'B': ['E'], 'C': ['D'], 'D': ['E'], 'E': []}", "print(shortest_steps(g, 'A', 'E'))"],
             answer=5, fix="        node, dist = queue.popleft()", expected_output="2",
             hint="BFS needs a queue (first in, first out). What does pop() take from a deque?",
             explanation="pop() takes the newest item, which turns BFS into DFS and finds a longer path. popleft() keeps it level by level."),
    ],
}

for _topic_id, _items in EXERCISES.items():
    ENRICHMENT[_topic_id]["exercises"] = _items
