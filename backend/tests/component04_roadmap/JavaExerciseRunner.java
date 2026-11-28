// Owner: Dewmi - Component 04. Drafted with an AI assistant, checked by the curriculum validator and tests, and reviewed by the C4 author.
// Test helper for exercise_runner.py: runs many Java exercise programs in ONE JVM, so checking every order of an
// order_steps exercise does not start a JVM per program. Launched as a single-file program: java JavaExerciseRunner.java
//
// Input (stdin):  one program per line, Base64 (UTF-8). Each program is a complete source whose entry class is Main.
// Output (stdout): one line per program, Base64 (UTF-8) of its observed output: what it printed (line ends normalised to
//                  \n, outer whitespace stripped), then - on its own line - the simple name of an uncaught exception
//                  (e.g. ArithmeticException), "compile error" when javac rejects it, or "Timeout".
// Each program is compiled in memory with javax.tools (JDK only) and loaded by its own class loader.
import javax.tools.*;
import java.io.*;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;

public class JavaExerciseRunner {
    static final long TIME_LIMIT_SECONDS = 10;

    static final class Source extends SimpleJavaFileObject {
        final String code;
        Source(String className, String code) {
            super(URI.create("string:///" + className + ".java"), Kind.SOURCE);
            this.code = code;
        }
        @Override public CharSequence getCharContent(boolean ignoreEncodingErrors) { return code; }
    }

    static final class ClassBytes extends SimpleJavaFileObject {
        final ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        ClassBytes(String className) { super(URI.create("bytes:///" + className.replace('.', '/') + ".class"), Kind.CLASS); }
        @Override public OutputStream openOutputStream() { return bytes; }
    }

    public static void main(String[] args) throws Exception {
        JavaCompiler javac = ToolProvider.getSystemJavaCompiler();
        if (javac == null) {
            System.err.println("No Java compiler: a JDK (not only a JRE) is needed");
            System.exit(2);
        }
        PrintStream realOut = System.out;
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
        ExecutorService pool = Executors.newCachedThreadPool(r -> { Thread t = new Thread(r); t.setDaemon(true); return t; });
        String line;
        while ((line = in.readLine()) != null) {
            if (line.isBlank()) continue;
            String source = new String(Base64.getDecoder().decode(line.strip()), StandardCharsets.UTF_8);
            String observed = runOne(javac, pool, source, realOut);
            realOut.println(Base64.getEncoder().encodeToString(observed.getBytes(StandardCharsets.UTF_8)));
            realOut.flush();
        }
        System.exit(0);                                  // a timed-out program may still be running on a daemon thread
    }

    static String runOne(JavaCompiler javac, ExecutorService pool, String source, PrintStream realOut) {
        Map<String, ClassBytes> classes = new HashMap<>();
        StandardJavaFileManager standard = javac.getStandardFileManager(null, null, StandardCharsets.UTF_8);
        JavaFileManager files = new ForwardingJavaFileManager<JavaFileManager>(standard) {
            @Override
            public JavaFileObject getJavaFileForOutput(Location location, String className, JavaFileObject.Kind kind, FileObject sibling) {
                ClassBytes out = new ClassBytes(className);
                classes.put(className, out);
                return out;
            }
        };
        DiagnosticCollector<JavaFileObject> diagnostics = new DiagnosticCollector<>();
        boolean compiled = javac.getTask(null, files, diagnostics, List.of("-proc:none", "-Xlint:none"), null,
                                         List.of(new Source("Main", source))).call();
        if (!compiled) return "compile error";
        ClassLoader loader = new ClassLoader(JavaExerciseRunner.class.getClassLoader()) {
            @Override protected Class<?> findClass(String name) throws ClassNotFoundException {
                ClassBytes found = classes.get(name);
                if (found == null) throw new ClassNotFoundException(name);
                byte[] b = found.bytes.toByteArray();
                return defineClass(name, b, 0, b.length);
            }
        };
        ByteArrayOutputStream buffer = new ByteArrayOutputStream();
        PrintStream captured = new PrintStream(buffer, true, StandardCharsets.UTF_8);
        String error = null;
        System.setOut(captured);
        try {
            Method main = loader.loadClass("Main").getMethod("main", String[].class);
            Future<?> run = pool.submit(() -> { main.invoke(null, (Object) new String[0]); return null; });
            run.get(TIME_LIMIT_SECONDS, TimeUnit.SECONDS);
        } catch (TimeoutException e) {
            error = "Timeout";
        } catch (ExecutionException e) {
            Throwable cause = e.getCause();
            if (cause instanceof InvocationTargetException && cause.getCause() != null) cause = cause.getCause();
            error = cause.getClass().getSimpleName();
        } catch (ReflectiveOperationException | InterruptedException e) {
            error = "no main: " + e.getClass().getSimpleName();
        } finally {
            captured.flush();
            System.setOut(realOut);
        }
        String text = buffer.toString(StandardCharsets.UTF_8).replace("\r\n", "\n").strip();
        if (error == null) return text;
        return text.isEmpty() ? error : text + "\n" + error;
    }
}
