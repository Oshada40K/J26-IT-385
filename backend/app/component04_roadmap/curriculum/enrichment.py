# Owner: Dewmi - Component 04. Extra teaching parts for every curated topic, used by the "lecture notes" lesson style:
#   from_zero    - an everyday analogy that explains the idea to a complete beginner
#   memory_trick - a short way to remember it
#   career_hack  - an interview / workplace tip (how the idea is checked in real jobs)
#   recall       - memory-test questions; the answer is hidden until the student reveals it (practice, not graded)
#   video        - one short YouTube video; title and channel are copied exactly from YouTube oEmbed on checked_on
# Written by the C4 author, not AI-generated. Merged into the topics by curriculum.load().

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
