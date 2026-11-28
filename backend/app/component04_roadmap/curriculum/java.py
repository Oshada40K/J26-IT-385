# Owner: Dewmi - Component 04. Curated lesson bank for Java (SK003). Drafted with an AI assistant, checked by the curriculum validator and tests, and reviewed by the C4 author.
SKILL_ID = "SK003"

TOPICS = [
    dict(
        id="java-b1", title="Types, variables and control flow", stage="Beginner", requires=[],
        objective="Declare variables with primitive types and String, predict int and double division, and use if/else, switch, for and while.",
        main_idea="Java is statically typed: every variable has a type that the compiler checks before the program runs. "
                  "Control flow (if, switch, loops) decides which statements run and how often.",
        explanation="Every Java program starts in public static void main(String[] args). Variables are declared with a type: "
                    "int count = 3; double price = 4.5; boolean done = false; char grade = 'A'; String name = \"Ama\";. int, "
                    "double, boolean and char are primitive types; String is an object (a reference type). The compiler rejects "
                    "mismatches such as int x = 3.5; (possible lossy conversion). Division of two ints is integer division: "
                    "7 / 2 is 3, and 7 % 2 is the remainder 1. Make one side a double, as in (double) 7 / 2, to get 3.5. "
                    "if / else if / else runs the first branch whose condition is true. switch picks a branch by value; the "
                    "modern form case \"A\" -> ... needs no break. for (int i = 0; i < 3; i++) repeats a known number of times; "
                    "while (condition) repeats until the condition is false. Statements end with ; and blocks use { }. "
                    "Use var only when the type is obvious from the right-hand side (var list = new ArrayList<String>();).",
        foundation=["Type first, then name: int age = 20;",
                    "int / int drops the decimals; cast to double to keep them.",
                    "for when you know how many times; while when you wait for a condition."],
        challenge="Write a program that prints the numbers 1 to 30, but Fizz for multiples of 3, Buzz for multiples of 5 and "
                  "FizzBuzz for both, using a for loop and the % operator.",
        example=dict(title="Grades and division", language="java",
                     code="public class Main {\n    public static void main(String[] args) {\n        int total = 7;\n        int people = 2;\n"
                          "        System.out.println(total / people);            // 3\n"
                          "        System.out.println((double) total / people);   // 3.5\n\n        int mark = 72;\n        String grade;\n"
                          "        if (mark >= 75) {\n            grade = \"Distinction\";\n        } else if (mark >= 50) {\n"
                          "            grade = \"Pass\";\n        } else {\n            grade = \"Fail\";\n        }\n"
                          "        System.out.println(grade);                     // Pass\n\n"
                          "        for (int i = 1; i <= 3; i++) {\n            System.out.print(i + \" \");          // 1 2 3\n        }\n    }\n}",
                     steps=["total / people divides two ints, so the decimal part is dropped: 3.",
                            "The cast (double) total makes it 7.0, so the result is 3.5.",
                            "Only the first true branch runs: 72 is not >= 75 but is >= 50, so Pass.",
                            "The for loop runs with i = 1, 2 and 3."]),
        career_examples=dict(data="Big data tools such as Hadoop and Spark run on the JVM; type errors are caught before a long job starts.",
                             software="Banking and enterprise systems are often written in Java because the compiler catches many mistakes early."),
        visual=dict(kind="table", caption="Common types", columns=["Type", "Holds", "Example"],
                    rows=[["int", "whole numbers", "int count = 3;"], ["double", "decimal numbers", "double height = 1.75;"],
                          ["boolean", "true or false", "boolean done = false;"], ["String", "text (an object)", "String name = \"Ama\";"]],
                    how_to_read="Pick the row that matches your data; the last column shows how to declare it."),
        key_ideas=["Every variable has a type checked by the compiler.", "int / int is integer division; % is the remainder.",
                   "if/else if/else runs only the first true branch.", "for for counting, while for waiting on a condition."],
        mistakes=["Expecting 7 / 2 to be 3.5.", "Comparing with = (assignment) instead of == in a condition."],
        practice="Write a program that converts a mark (0-100) to a grade with if/else, then prints the grades for 45, 50, 74 and 75.",
        practical=dict(task="Write a console program that prints a times table (1-10) for a number, and the sum and average of the results.",
                       rubric=["Correct types for each variable", "Loop produces all ten lines", "Average printed as a decimal, not integer division"]),
        next_link="Next you will organise code into methods and work with arrays and strings.",
        quiz=[
            dict(id="java-b1-q1", type="single", concept="integer division",
                 prompt="What does System.out.println(7 / 2); print?",
                 options=["3", "3.5", "4", "3.0"], answer=0,
                 explanation="Both values are ints, so Java does integer division and drops the decimal part."),
            dict(id="java-b1-q2", type="single", concept="types",
                 prompt="Which type fits a measurement such as 1.75 (metres)?",
                 options=["int", "double", "boolean", "char"], answer=1,
                 explanation="double holds decimal numbers; int only holds whole numbers."),
            dict(id="java-b1-q3", type="single", concept="type checking",
                 prompt="What happens with  int x = 3.5; ?",
                 options=["x is 3", "x is 4", "Compile error: possible lossy conversion from double to int", "A runtime exception"], answer=2,
                 explanation="Java does not silently drop the decimals; the compiler rejects the line. An explicit cast (int) 3.5 would give 3."),
        ],
        diagnostic=[
            dict(id="java-b1-d1", type="single", concept="loops",
                 prompt="How many times does the body of  for (int i = 0; i < 3; i++)  run?",
                 options=["2", "3", "4", "Forever"], answer=1,
                 explanation="i takes the values 0, 1 and 2; when i is 3 the condition i < 3 is false."),
            dict(id="java-b1-d2", type="single", concept="types",
                 prompt="In Java, what is a String?",
                 options=["A primitive type like int", "An object (a reference type)", "A keyword for char arrays", "A kind of int"], answer=1,
                 explanation="String is a class; its values are objects, which is why you compare them with equals (next topic)."),
        ],
    ),
    dict(
        id="java-b2", title="Methods, arrays and strings", stage="Beginner", requires=["java-b1"],
        objective="Write static methods with parameters and return values, use arrays with loops, and compare strings with equals.",
        main_idea="A method is a named block of code with inputs (parameters) and an output (return type). Arrays hold a "
                  "fixed number of values of one type. Strings are objects, so compare them with equals.",
        explanation="static double average(int[] marks) { ... } declares a method: its return type (double), name, and "
                    "parameters with types. void means it returns nothing. Call it with average(myMarks). A method should do "
                    "one job and have a verb name. Arrays: int[] marks = {72, 45, 88}; or new int[3] (filled with 0). Indexes "
                    "run from 0 to marks.length - 1; using marks[3] here throws ArrayIndexOutOfBoundsException at runtime. "
                    "Loop with for (int i = 0; i < marks.length; i++) or the enhanced loop for (int m : marks) when you do not "
                    "need the index. Strings: s.length(), s.toUpperCase(), s.contains(\"java\"), s.substring(0, 3), and "
                    "String.join. == on objects compares whether two variables point to the same object; to compare the text "
                    "use a.equals(b) (or equalsIgnoreCase). Strings are immutable: toUpperCase returns a new String.",
        foundation=["Method header: return type, name, (parameters).",
                    "Array indexes: 0 to length - 1.",
                    "Strings: equals for text, never ==."],
        challenge="Write a method that returns the most frequent character in a String, with a helper method for counting, "
                  "and test it with three inputs including an empty string.",
        example=dict(title="Methods with arrays and strings", language="java",
                     code="public class Main {\n    static double average(int[] marks) {\n        int total = 0;\n"
                          "        for (int m : marks) {\n            total += m;\n        }\n        return (double) total / marks.length;\n    }\n\n"
                          "    static boolean isYes(String answer) {\n        return answer.trim().equalsIgnoreCase(\"yes\");\n    }\n\n"
                          "    public static void main(String[] args) {\n        int[] marks = {72, 45, 88};\n"
                          "        System.out.println(average(marks));   // 68.33333333333333\n"
                          "        System.out.println(isYes(\" YES \"));    // true\n    }\n}",
                     steps=["average takes an int array and returns a double.",
                            "The enhanced for loop adds each mark without an index.",
                            "The cast avoids integer division: 205 / 3.0.",
                            "isYes compares text with equalsIgnoreCase after trimming spaces."]),
        career_examples=dict(data="Data-processing code in Java splits work into small methods (parse, clean, summarise) that can be tested one by one.",
                             software="Code reviews ask for short methods with clear names; comparing strings with == is a classic bug they catch."),
        key_ideas=["Methods: return type, name, parameters.", "void returns nothing.",
                   "Arrays have fixed length; indexes start at 0.", "Compare Strings with equals."],
        mistakes=["Looping with i <= array.length, which goes one past the end.", "Comparing strings with ==."],
        practice="Write methods max(int[] values) and countWords(String sentence) and call them from main.",
        practical=dict(task="Write a grade report program with methods for average, highest and lowest mark, and a method that formats one line of the report.",
                       rubric=["Each method does one job and has a clear name", "No index out of bounds for any input array",
                               "Strings compared with equals"]),
        next_link="Next you will model real things with classes, constructors and interfaces.",
        quiz=[
            dict(id="java-b2-q1", type="single", concept="string comparison",
                 prompt="What is wrong with  if (input == \"yes\")  for a String input?",
                 options=["== compares object references; use input.equals(\"yes\")", "Nothing, == compares the text",
                          "It should be input = \"yes\"", "Strings cannot be compared in Java"], answer=0,
                 explanation="== checks whether both refer to the same object; equals compares the characters."),
            dict(id="java-b2-q2", type="single", concept="array indexes",
                 prompt="int[] a = new int[3];  System.out.println(a[3]);  What happens?",
                 options=["It prints 0", "It prints null", "ArrayIndexOutOfBoundsException at runtime", "A compile error"], answer=2,
                 explanation="The valid indexes are 0, 1 and 2. The compiler does not check index values, so the error happens when it runs."),
            dict(id="java-b2-q3", type="single", concept="return types",
                 prompt="A method is declared  static int square(int n).  What must it do?",
                 options=["Return an int value", "Print the result", "Return nothing", "Take no parameters"], answer=0,
                 explanation="The return type int means every path through the method must return an int."),
        ],
        diagnostic=[
            dict(id="java-b2-d1", type="single", concept="arrays",
                 prompt="int[] marks = {5, 8, 2};  What is marks.length?",
                 options=["2", "3", "8", "4"], answer=1,
                 explanation="length is the number of elements: 3. The last index is 2."),
            dict(id="java-b2-d2", type="single", concept="return types",
                 prompt="What does the return type void mean?",
                 options=["The method returns no value", "The method returns null", "The method is empty", "The method is private"], answer=0,
                 explanation="void methods do something (for example print) but give no value back."),
        ],
    ),
    dict(
        id="java-i1", title="Classes, constructors and interfaces", stage="Intermediate", requires=["java-b2"],
        objective="Write classes with private fields, constructors, this, getters and toString; implement an interface; know static from instance members.",
        main_idea="A class is a blueprint for objects: fields hold each object's data and methods define what it can do. An "
                  "interface is a contract: any class that implements it promises to provide its methods.",
        explanation="class Account { private int balance; ... } declares fields; private means only code in the class can "
                    "touch them, so other code must use methods such as deposit(amount), which can check the rules "
                    "(encapsulation). A constructor has the class name and no return type and sets the starting state: "
                    "Account(String owner) { this.owner = owner; }. this.owner is the field; owner alone is the parameter. "
                    "If you write no constructor, Java provides an empty no-argument one. new Account(\"Ama\") creates an "
                    "object. Override public String toString() to control how it prints. An instance field belongs to each "
                    "object; a static field is shared by the whole class (for example a counter of accounts). An interface "
                    "lists methods without bodies: interface Shape { double area(); }. class Square implements Shape must "
                    "provide public double area(). Code can then work with any Shape (Shape s = new Square(3);), which is "
                    "polymorphism. A class extends one class but can implement many interfaces. For simple data carriers, "
                    "a record (record Point(int x, int y) {}) generates the constructor, getters, equals and toString.",
        foundation=["Class = blueprint; object = one thing built with new.",
                    "private fields + public methods = encapsulation.",
                    "implements = 'I promise to provide these methods'."],
        challenge="Design an interface PaymentMethod with pay(double amount) and two classes (Card, Wallet) with their own rules; "
                  "write one method that takes a List<PaymentMethod> and pays with each.",
        example=dict(title="An account and a shape", language="java",
                     code="interface Shape {\n    double area();\n}\n\nclass Circle implements Shape {\n    private final double radius;\n"
                          "    Circle(double radius) { this.radius = radius; }\n    public double area() { return Math.PI * radius * radius; }\n}\n\n"
                          "class Account {\n    private static int created = 0;   // shared by all accounts\n    private final String owner;\n"
                          "    private int balance;\n\n    Account(String owner) {\n        this.owner = owner;\n        created++;\n    }\n\n"
                          "    void deposit(int amount) {\n        if (amount <= 0) throw new IllegalArgumentException(\"Amount must be positive\");\n"
                          "        balance += amount;\n    }\n\n    @Override\n    public String toString() { return owner + \": \" + balance; }\n}\n\n"
                          "public class Main {\n    public static void main(String[] args) {\n        Account a = new Account(\"Ama\");\n"
                          "        a.deposit(500);\n        System.out.println(a);                 // Ama: 500\n"
                          "        Shape s = new Circle(1);\n        System.out.printf(\"%.2f%n\", s.area());   // 3.14\n    }\n}",
                     steps=["Circle implements Shape, so it must provide area(); a Circle can be stored in a Shape variable.",
                            "Account's fields are private; deposit is the only way to change balance, and it checks the amount.",
                            "The constructor uses this.owner to set the field from the parameter, and counts accounts in a static field.",
                            "println calls toString automatically."]),
        career_examples=dict(data="Data pipelines in Java define interfaces such as Reader and Writer so a CSV source can be swapped for a database source.",
                             software="Spring Boot applications are built from classes that implement interfaces (services, repositories), which makes them easy to test."),
        key_ideas=["Fields private, behaviour public.", "Constructors set the starting state; this.field = parameter.",
                   "static = one per class; instance = one per object.", "Program to interfaces: Shape s = new Square(3);"],
        mistakes=["Writing name = name; in a constructor, so the field stays null.", "Making fields public so any code can put an object in an invalid state."],
        practice="Write a Book class (title, author, pages) with a constructor, getters and toString, and create three books.",
        practical=dict(task="Model a small library: an interface Borrowable, two classes that implement it, and a main method that uses them through the interface.",
                       rubric=["Fields are private with methods that protect the rules", "Constructors set all required fields",
                               "Main code uses the interface type"]),
        next_link="Next you will store many objects in collections: lists and maps.",
        quiz=[
            dict(id="java-i1-q1", type="single", concept="encapsulation",
                 prompt="Why make fields private and change them only through methods?",
                 options=["So other code can only change the data through methods that check the rules", "To make the program faster",
                          "Because Java requires every field to be private", "So the class itself cannot read them"], answer=0,
                 explanation="Encapsulation protects the object's state; methods such as withdraw can refuse invalid changes."),
            dict(id="java-i1-q2", type="single", concept="constructors",
                 prompt="A class has no constructor written in it. What happens when you call new on it?",
                 options=["Java provides a default no-argument constructor", "The class cannot be created", "A compile error",
                          "All fields must be static"], answer=0,
                 explanation="If no constructor is written, the compiler adds an empty no-argument constructor."),
            dict(id="java-i1-q3", type="single", concept="interfaces",
                 prompt="interface Pet { String sound(); }  What must  class Dog implements Pet  contain?",
                 options=["A public String sound() method (unless Dog is abstract)", "An extends Pet clause", "A main method", "Nothing"], answer=0,
                 explanation="Implementing an interface is a promise to provide all its methods; the compiler checks it."),
        ],
        diagnostic=[
            dict(id="java-i1-d1", type="single", concept="static members",
                 prompt="What does static mean on a field?",
                 options=["There is one value shared by all objects of the class", "The value can never change",
                          "The field is private", "Each object gets its own copy"], answer=0,
                 explanation="A static field belongs to the class itself. A value that cannot change is final, which is different."),
            dict(id="java-i1-d2", type="single", concept="this",
                 prompt="In a constructor, what does  this.name = name;  do?",
                 options=["Copies the parameter name into the object's field name", "Compares the field and the parameter",
                          "Creates a new class", "Nothing"], answer=0,
                 explanation="this.name is the field of the object being created; name alone is the parameter."),
        ],
    ),
    dict(
        id="java-i2", title="Collections and generics", stage="Intermediate", requires=["java-i1"],
        objective="Use List and ArrayList, Map and HashMap with generic types, iterate over them, and avoid boxing and modification pitfalls.",
        main_idea="Collections hold groups of objects and can grow. A List keeps items in order; a Map looks values up by a "
                  "key. Generics (List<String>) tell the compiler what type they hold.",
        explanation="List<String> skills = new ArrayList<>(); creates a growable list (the <> lets Java infer the type). add, "
                    "get(index), size(), contains, remove and sort are the common methods. List.of(\"a\", \"b\") makes a "
                    "list that cannot be changed. Map<String, Integer> marks = new HashMap<>(); stores key-value pairs: put "
                    "adds or replaces (keys are unique), get returns the value or null, getOrDefault(key, 0) avoids null, "
                    "containsKey checks, and for (Map.Entry<String, Integer> e : marks.entrySet()) loops over the pairs. "
                    "HashMap does not keep any order; use LinkedHashMap for insertion order or TreeMap for sorted keys. A Set "
                    "(HashSet) keeps unique values. Generics need object types, so a list of numbers is List<Integer>; Java "
                    "converts between int and Integer automatically (autoboxing), but an Integer can be null. Do not add or "
                    "remove items of a collection inside a for-each loop over it: that throws "
                    "ConcurrentModificationException. Use removeIf(m -> m < 50) or an Iterator instead. Declare variables with "
                    "the interface type (List, Map) so the implementation can change.",
        foundation=["List = ordered items; Map = look up by key; Set = unique items.",
                    "List<Integer>, not List<int>.",
                    "Never remove from a list inside its own for-each loop."],
        challenge="Count how often each word appears in a paragraph with a Map, then print the five most frequent words "
                  "sorted by count.",
        example=dict(title="Skills list and word counts", language="java",
                     code="import java.util.*;\n\npublic class Main {\n    public static void main(String[] args) {\n"
                          "        List<String> skills = new ArrayList<>(List.of(\"Java\", \"SQL\"));\n        skills.add(\"Git\");\n"
                          "        System.out.println(skills.get(0) + \" of \" + skills.size());   // Java of 3\n\n"
                          "        Map<String, Integer> counts = new HashMap<>();\n"
                          "        for (String w : \"to be or not to be\".split(\" \")) {\n"
                          "            counts.put(w, counts.getOrDefault(w, 0) + 1);\n        }\n"
                          "        System.out.println(counts.get(\"be\"));                          // 2\n\n"
                          "        skills.removeIf(s -> s.length() < 4);\n        System.out.println(skills);                                  // [Java]\n"
                          "    }\n}",
                     steps=["new ArrayList<>(List.of(...)) makes a list that can still grow; add appends Git.",
                            "getOrDefault returns 0 the first time a word is seen, so the count starts at 1.",
                            "put with an existing key replaces its value.",
                            "removeIf safely removes the items that match the condition (SQL and Git)."]),
        career_examples=dict(data="Aggregating records by key (sales per region) with a Map is the core of many Java data jobs.",
                             software="Almost every Java service passes List and Map objects between layers, for example the results of a database query."),
        key_ideas=["List for order, Map for lookup, Set for uniqueness.", "Generic types give compile-time checks.",
                   "Declare with the interface: List<String> x = new ArrayList<>();", "Use removeIf or an Iterator to remove while iterating."],
        mistakes=["Removing items inside a for-each loop over the same list.", "Expecting a HashMap to keep insertion or sorted order."],
        practice="Store five students and their marks in a Map, print them, and build a List of the names of students who passed.",
        practical=dict(task="Write a small inventory program: a Map from product name to quantity with methods to add stock, sell and list items below a threshold.",
                       rubric=["Uses generic types everywhere", "Handles unknown products without NullPointerException",
                               "No ConcurrentModificationException when removing"]),
        next_link="Next you will handle errors with exceptions and close resources safely.",
        quiz=[
            dict(id="java-i2-q1", type="single", concept="choosing a collection",
                 prompt="Which collection fits looking up a student's mark by their student id?",
                 options=["ArrayList<Integer>", "HashMap<String, Integer>", "int[]", "String"], answer=1,
                 explanation="A Map looks up a value (the mark) by a key (the id) directly."),
            dict(id="java-i2-q2", type="single", concept="generics and boxing",
                 prompt="Why do we write List<Integer> and not List<int>?",
                 options=["Generics need object types; int values are autoboxed to Integer", "int is too small for lists",
                          "List<int> works but is deprecated", "There is no reason"], answer=0,
                 explanation="Type parameters must be reference types, so the wrapper class Integer is used."),
            dict(id="java-i2-q3", type="multi", concept="List and Map",
                 prompt="Which statements are true? Select all that apply.",
                 options=["An ArrayList keeps insertion order and allows duplicates", "The keys of a HashMap are unique",
                          "A HashMap keeps its keys sorted", "get(index) on an ArrayList is fast"], answer=[0, 1, 3],
                 explanation="Lists keep order and duplicates; map keys are unique; HashMap has no guaranteed order (TreeMap sorts); "
                             "ArrayList reads by index in constant time."),
        ],
        diagnostic=[
            dict(id="java-i2-d1", type="single", concept="Map put",
                 prompt="map.put(\"a\", 1);  map.put(\"a\", 2);  What does map.get(\"a\") return?",
                 options=["1", "2", "[1, 2]", "null"], answer=1,
                 explanation="put with an existing key replaces the old value."),
            dict(id="java-i2-d2", type="single", concept="modifying while iterating",
                 prompt="What usually happens if you remove items from an ArrayList inside a for-each loop over it?",
                 options=["ConcurrentModificationException; use removeIf or an Iterator", "It works fine",
                          "A compile error", "Items are skipped silently, which is the recommended way"], answer=0,
                 explanation="The for-each loop's iterator notices the change and throws; removeIf and Iterator.remove are safe."),
        ],
    ),
    dict(
        id="java-a1", title="Exceptions and try-with-resources", stage="Advanced", requires=["java-i2"],
        objective="Tell checked from unchecked exceptions, use try/catch/finally and try-with-resources, and create and throw custom exceptions.",
        main_idea="An exception stops normal flow when something goes wrong. Catch it where you can do something useful, let "
                  "it travel up otherwise, and use try-with-resources so files and connections are always closed.",
        explanation="When code throws an exception, the rest of the try block is skipped and Java looks for a matching catch, "
                    "first in the current method and then in its callers; if none matches, the program stops with a stack "
                    "trace. Checked exceptions (Exception subclasses such as IOException) must be caught or declared with "
                    "throws in the method header; the compiler enforces it. Unchecked exceptions (RuntimeException "
                    "subclasses such as NullPointerException, IllegalArgumentException, ArithmeticException) usually mean a "
                    "bug or bad input and need not be declared. Order catch blocks from specific to general: catch "
                    "(FileNotFoundException e) before catch (IOException e), or the code does not compile. finally runs "
                    "whether or not an exception happened. try (var reader = Files.newBufferedReader(path)) { ... } is "
                    "try-with-resources: any AutoCloseable declared in the brackets is closed automatically, even when an "
                    "exception is thrown. Create your own exception by extending Exception (checked) or RuntimeException "
                    "(unchecked), and throw it with a clear message: throw new InsufficientFundsException(\"Not enough money\"). "
                    "Never catch an exception and do nothing with it.",
        foundation=["Checked = the compiler makes you handle it; unchecked = usually a bug.",
                    "catch specific exceptions first, general ones last.",
                    "Resource in try ( ... ) = closed automatically."],
        challenge="Write a method that reads numbers from a text file with try-with-resources, skips invalid lines with a "
                  "warning, and throws a custom checked exception when the file has no valid numbers.",
        example=dict(title="Withdraw with a custom exception", language="java",
                     code="class InsufficientFundsException extends Exception {\n"
                          "    InsufficientFundsException(String message) { super(message); }\n}\n\n"
                          "class Account {\n    private int balance = 100;\n\n"
                          "    void withdraw(int amount) throws InsufficientFundsException {\n"
                          "        if (amount <= 0) throw new IllegalArgumentException(\"Amount must be positive\");\n"
                          "        if (amount > balance) throw new InsufficientFundsException(\"Balance is only \" + balance);\n"
                          "        balance -= amount;\n    }\n}\n\npublic class Main {\n    public static void main(String[] args) {\n"
                          "        Account a = new Account();\n        try {\n            a.withdraw(500);\n"
                          "        } catch (InsufficientFundsException e) {\n            System.out.println(\"Sorry: \" + e.getMessage());\n"
                          "        } finally {\n            System.out.println(\"Transaction finished\");\n        }\n    }\n}",
                     steps=["InsufficientFundsException extends Exception, so it is checked: withdraw must declare it with throws.",
                            "A bad amount is a programming error, so it uses the unchecked IllegalArgumentException.",
                            "main catches the checked exception and shows its message: Sorry: Balance is only 100.",
                            "finally runs in both cases."]),
        career_examples=dict(data="Data import jobs catch bad records, log them and continue, instead of failing the whole run.",
                             software="APIs map exceptions to HTTP errors (for example a NotFoundException to 404) in one central place."),
        key_ideas=["Checked exceptions: catch or declare.", "Catch specific before general.",
                   "finally always runs; try-with-resources always closes.", "Custom exceptions with clear messages describe domain errors."],
        mistakes=["Empty catch blocks that hide errors.", "Catching Exception everywhere instead of the specific exceptions you can handle."],
        practice="Write a method that parses an age from a String, throws IllegalArgumentException for negative values, and test it in a try/catch.",
        practical=dict(task="Add error handling to an earlier program: custom exceptions for invalid input, try-with-resources for file reading, and clear messages.",
                       rubric=["At least one custom exception", "Resources closed with try-with-resources", "No empty catch blocks"]),
        next_link="Next you will write shorter, clearer data code with lambdas and the Stream API.",
        quiz=[
            dict(id="java-a1-q1", type="single", concept="checked exceptions",
                 prompt="Which of these is a checked exception?",
                 options=["IOException", "NullPointerException", "ArithmeticException", "IllegalArgumentException"], answer=0,
                 explanation="IOException extends Exception but not RuntimeException, so it is checked. The others are RuntimeExceptions."),
            dict(id="java-a1-q2", type="single", concept="finally",
                 prompt="When does a finally block run?",
                 options=["Whether or not an exception was thrown", "Only when an exception was thrown",
                          "Only when no exception was thrown", "Never if the try block has a return"], answer=0,
                 explanation="finally runs after try (and catch) in every case, even after a return in try."),
            dict(id="java-a1-q3", type="short", concept="try-with-resources",
                 prompt="In one sentence: what does try-with-resources do for you?",
                 answer=[["close", "closes", "closed"]],
                 sample_answer="It closes the resource automatically when the block ends, even if an exception is thrown.",
                 explanation="Any AutoCloseable declared in try ( ... ) is closed automatically, so you cannot forget it."),
        ],
        diagnostic=[
            dict(id="java-a1-d1", type="single", concept="checked exceptions",
                 prompt="A method calls code that can throw a checked exception. What must the method do?",
                 options=["Catch it, or declare it with throws", "Always catch Exception", "Return null", "Be static"], answer=0,
                 explanation="The compiler requires a checked exception to be handled or declared."),
            dict(id="java-a1-d2", type="single", concept="catch order",
                 prompt="FileNotFoundException is a subclass of IOException. Which catch order compiles?",
                 options=["catch (FileNotFoundException e) before catch (IOException e)",
                          "catch (IOException e) before catch (FileNotFoundException e)", "Both orders", "Neither order"], answer=0,
                 explanation="A catch for a subclass after its superclass can never run, so javac rejects it ('has already been caught')."),
        ],
    ),
    dict(
        id="java-a2", title="Lambdas and the Stream API", stage="Advanced", requires=["java-a1"],
        objective="Write lambdas for functional interfaces, process collections with stream().filter().map().collect(), and use Optional safely.",
        main_idea="A lambda is a short function you can pass around. Streams describe what to do with a collection (filter, "
                  "map, collect) instead of writing the loop yourself. Optional makes 'maybe no value' explicit.",
        explanation="A functional interface has exactly one abstract method, for example Function<T, R> (apply), Predicate<T> "
                    "(test), Consumer<T> (accept), Supplier<T> (get) and Comparator<T> (compare). A lambda implements it: "
                    "Predicate<String> isLong = s -> s.length() > 5;. A method reference is a shorter form when a lambda only "
                    "calls one method: String::toUpperCase. Streams: list.stream() starts a pipeline; intermediate "
                    "operations (filter, map, sorted, distinct) describe steps and are lazy; a terminal operation (collect, "
                    "toList, count, sum, forEach, findFirst) runs the whole pipeline. Collectors.toList() and "
                    "Collectors.groupingBy(...) build results. A stream does not change its source list, and can be used "
                    "only once. Some terminal operations (max, min, findFirst) return Optional<T> because there may be no "
                    "result: use orElse(default), orElseThrow() or ifPresent(...) instead of calling get() blindly. Keep "
                    "lambdas short and free of side effects; a plain loop is still fine when it is clearer.",
        foundation=["Lambda = (parameters) -> result.",
                    "stream() ... filter ... map ... collect: nothing runs until the terminal step.",
                    "Optional = a box that may be empty; open it with orElse."],
        challenge="Given a list of Employee records (name, department, salary), use groupingBy to compute the average salary "
                  "per department and print the departments sorted by that average.",
        example=dict(title="Filtering and summarising jobs", language="java",
                     code="import java.util.*;\nimport java.util.stream.*;\n\nrecord Job(String title, String city, int salary) {}\n\n"
                          "public class Main {\n    public static void main(String[] args) {\n        List<Job> jobs = List.of(\n"
                          "            new Job(\"Java Developer\", \"Colombo\", 250000),\n            new Job(\"Tester\", \"Kandy\", 150000),\n"
                          "            new Job(\"Backend Engineer\", \"Colombo\", 300000));\n\n        List<String> colombo = jobs.stream()\n"
                          "            .filter(j -> j.city().equals(\"Colombo\"))\n            .map(Job::title)\n"
                          "            .collect(Collectors.toList());\n        System.out.println(colombo);   // [Java Developer, Backend Engineer]\n\n"
                          "        Optional<Job> best = jobs.stream().max(Comparator.comparingInt(Job::salary));\n"
                          "        System.out.println(best.map(Job::title).orElse(\"none\"));   // Backend Engineer\n    }\n}",
                     steps=["filter keeps the Colombo jobs with a lambda; map(Job::title) turns each job into its title.",
                            "collect runs the pipeline and builds a new List; jobs itself is unchanged.",
                            "max returns an Optional because the list could be empty.",
                            "map and orElse read the Optional safely, with a default for the empty case."]),
        career_examples=dict(data="Streams with groupingBy summarise records (totals per category) in a few readable lines.",
                             software="Modern Java code bases (Spring Boot services) use streams and Optional everywhere; interviewers often ask for a stream solution."),
        key_ideas=["Lambdas implement functional interfaces.", "Intermediate operations are lazy; a terminal operation runs them.",
                   "Streams do not change the source collection.", "Read Optional with orElse, orElseThrow or ifPresent."],
        mistakes=["Calling Optional.get() without checking, which throws NoSuchElementException on an empty Optional.",
                  "Changing outside variables or the source list inside a stream lambda."],
        practice="Given a list of words, use a stream to get the distinct words longer than 3 letters, in upper case and sorted.",
        practical=dict(task="Rewrite three loops from your earlier Java programs as streams, and replace one method that can return null with one that returns Optional.",
                       rubric=["Streams give the same results as the loops", "No side effects inside lambdas", "Optional is read without get()"]),
        next_link="You now have the core Java needed for frameworks such as Spring Boot, the next skill on many Java roadmaps.",
        quiz=[
            dict(id="java-a2-q1", type="single", concept="functional interfaces",
                 prompt="Where can a lambda be used in Java?",
                 options=["Wherever a functional interface (an interface with one abstract method) is expected", "As any class",
                          "As an array", "As a primitive value"], answer=0,
                 explanation="A lambda is an implementation of the single abstract method of a functional interface."),
            dict(id="java-a2-q2", type="single", concept="filter and map",
                 prompt="What does  List.of(1, 2, 3, 4).stream().filter(n -> n % 2 == 0).map(n -> n * 10).collect(Collectors.toList())  return?",
                 options=["[20, 40]", "[10, 30]", "[2, 4]", "[10, 20, 30, 40]"], answer=0,
                 explanation="filter keeps the even numbers 2 and 4; map multiplies them by 10."),
            dict(id="java-a2-q3", type="single", concept="Optional",
                 prompt="Optional<String> city = Optional.empty();  What does city.orElse(\"none\") return?",
                 options=["\"none\"", "null", "It throws NoSuchElementException", "Optional.empty"], answer=0,
                 explanation="orElse returns the value if there is one, otherwise the default you pass."),
        ],
        diagnostic=[
            dict(id="java-a2-d1", type="single", concept="lazy streams",
                 prompt="When do intermediate operations such as filter and map run?",
                 options=["Only when a terminal operation such as collect runs", "Immediately when they are called", "Twice",
                          "In a new thread"], answer=0,
                 explanation="Streams are lazy: the pipeline runs when a terminal operation asks for the result."),
            dict(id="java-a2-d2", type="single", concept="method references",
                 prompt="Which of these is a method reference?",
                 options=["String::toUpperCase", "s -> s.toUpperCase()", "new String()", "String.toUpperCase"], answer=0,
                 explanation="Class::method is method-reference syntax. s -> s.toUpperCase() does the same, but it is a lambda."),
        ],
    ),
]
