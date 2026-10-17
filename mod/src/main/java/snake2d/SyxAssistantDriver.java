package snake2d;

import org.lwjgl.glfw.*;
import snake2d.util.file.SnakeImage;
import java.nio.file.Path;
import static org.lwjgl.glfw.GLFW.*;

/** Version-specific, in-process input/capture adapter. Never injects desktop input. */
public final class SyxAssistantDriver extends CORE_RESOURCE {
    private final Runnable takeover, disposed;
    private final long window;
    private GLFWKeyCallback originalKey, wrappedKey;
    private GLFWMouseButtonCallback originalMouse, wrappedMouse;
    private GLFWScrollCallback originalScroll, wrappedScroll;
    private GLFWCharCallback originalChar;
    private boolean closed;
    public SyxAssistantDriver(Runnable takeover, Runnable disposed) {
        this.takeover = takeover; this.disposed = disposed;
        window = CORE.getGraphics().getWindow();
        originalKey = glfwSetKeyCallback(window, null);
        wrappedKey = GLFWKeyCallback.create((w,k,s,a,m) -> { if(a==GLFW_PRESS) takeover.run(); if (originalKey != null) originalKey.invoke(w,k,s,a,m); });
        glfwSetKeyCallback(window, wrappedKey);
        originalMouse = glfwSetMouseButtonCallback(window, null);
        wrappedMouse = GLFWMouseButtonCallback.create((w,b,a,m) -> { if(a==GLFW_PRESS) takeover.run(); if (originalMouse != null) originalMouse.invoke(w,b,a,m); });
        glfwSetMouseButtonCallback(window, wrappedMouse);
        originalScroll = glfwSetScrollCallback(window, null);
        wrappedScroll = GLFWScrollCallback.create((w,x,y) -> { takeover.run(); if (originalScroll != null) originalScroll.invoke(w,x,y); });
        glfwSetScrollCallback(window, wrappedScroll);
        originalChar = glfwSetCharCallback(window, null);
        glfwSetCharCallback(window, originalChar);
        CORE.addDisposable(this);
    }
    public boolean focused() { return !closed && CORE.getGraphics()!=null && CORE.getGraphics().focused(); }
    public int width() { return CORE.getGraphics().nativeWidth; }
    public int height() { return CORE.getGraphics().nativeHeight; }
    public void capture(Path target) {
        if (closed) throw new IllegalStateException("Game driver closed");
        runGl(() -> {
            SnakeImage image = new SnakeImage(width(), height());
            try { CORE.getGraphics().copyFB(image, 0, 0); image.save(target.toString()); }
            finally { image.dispose(); }
        });
    }
    public void action(String operation, int x, int y, String value, Runnable validate) {
        if (!focused()) throw new IllegalStateException("Focus the game window before allowing input");
        runGl(() -> {
            if (!focused()) throw new IllegalStateException("Game focus changed");
            validate.run();
            if (operation.equals("click") || operation.equals("hover") || operation.equals("scroll")) {
                float sx = x * CORE.getGraphics().mouseWindow.x() / (float)width();
                float sy = y * CORE.getGraphics().mouseWindow.y() / (float)height();
                CORE.getInput().getMouse().setMousePoss(sx, sy);
                CORE.getInput().getMouse().getCoo().set(x,y);
            }
            switch(operation) {
                case "hover": break;
                case "click":
                    int b = value.equals("right") ? GLFW_MOUSE_BUTTON_RIGHT : GLFW_MOUSE_BUTTON_LEFT;
                    originalMouse.invoke(window,b,GLFW_PRESS,0); originalMouse.invoke(window,b,GLFW_RELEASE,0); break;
                case "scroll": originalScroll.invoke(window,0,Integer.parseInt(value)); break;
                case "key":
                    int key = key(value);
                    originalKey.invoke(window,key,0,GLFW_PRESS,0); originalKey.invoke(window,key,0,GLFW_RELEASE,0); break;
                case "text":
                    if (CORE.getInput().getKeyboard().listener == null) throw new IllegalStateException("No focused game text field");
                    if (value.length()>64) throw new IllegalArgumentException("At most 64 characters per action");
                    value.codePoints().forEach(c -> { if (c<32 || c>65535) throw new IllegalArgumentException("Unsupported text character"); });
                    value.codePoints().forEach(c -> originalChar.invoke(window,c)); break;
                default: throw new IllegalArgumentException("Unsupported UI action");
            }
        });
    }
    private static void runGl(Runnable work) {
        java.util.concurrent.atomic.AtomicReference<RuntimeException> failure = new java.util.concurrent.atomic.AtomicReference<>();
        new CORE.GlJob() { protected void doJob() {
            try { work.run(); } catch (RuntimeException e) { failure.set(e); }
        }}.perform();
        if (failure.get()!=null) throw failure.get();
    }
    private static int key(String key) {
        switch(key) {
            case "SPACE": return GLFW_KEY_SPACE;
            case "ENTER": return GLFW_KEY_ENTER;
            case "TAB": return GLFW_KEY_TAB;
            case "BACKSPACE": return GLFW_KEY_BACKSPACE;
            case "UP": return GLFW_KEY_UP;
            case "DOWN": return GLFW_KEY_DOWN;
            case "LEFT": return GLFW_KEY_LEFT;
            case "RIGHT": return GLFW_KEY_RIGHT;
        }
        if (key.matches("[A-Z0-9]")) return key.charAt(0);
        throw new IllegalArgumentException("Key not allowlisted");
    }
    @Override public void dis() {
        if (closed) return;
        closed = true; takeover.run();
        glfwSetKeyCallback(window,originalKey); glfwSetMouseButtonCallback(window,originalMouse); glfwSetScrollCallback(window,originalScroll);
        wrappedKey.close(); wrappedMouse.close(); wrappedScroll.close();
        disposed.run();
    }
}
