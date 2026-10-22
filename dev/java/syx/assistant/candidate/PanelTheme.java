package syx.assistant.candidate;

/** Detached candidate palette. Contrast is an abstract sRGB calculation, not native pixel proof. */
public final class PanelTheme {
    public final String name;public final int background,accent,bodyText,accentText;
    private PanelTheme(String name,int background,int accent){
        this.name=name;this.background=background;this.accent=accent;
        bodyText=ink(background);accentText=ink(accent);
    }
    public static PanelTheme preset(String name){
        switch(name){
        case "Forest":return new PanelTheme(name,0x17251D,0x87A68D);
        case "Parchment":return new PanelTheme(name,0xE7DDC6,0x745137);
        case "Night":return new PanelTheme(name,0x171D2B,0x94A7D1);
        default:throw new IllegalArgumentException("Unknown palette");
        }
    }
    public PanelTheme withAccent(String hex){
        if(hex==null||!hex.matches("#?[0-9a-fA-F]{6}"))throw new IllegalArgumentException("Use six hexadecimal digits");
        return new PanelTheme(name,background,Integer.parseInt(hex.startsWith("#")?hex.substring(1):hex,16));
    }
    public String accentHex(){return String.format(java.util.Locale.ROOT,"#%06X",accent);}
    private static double component(int value){double c=value/255.0;return c<=.04045?c/12.92:Math.pow((c+.055)/1.055,2.4);}
    private static double luminance(int rgb){return .2126*component((rgb>>16)&255)+.7152*component((rgb>>8)&255)+.0722*component(rgb&255);}
    public static double contrast(int a,int b){double x=luminance(a),y=luminance(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);}
    private static int ink(int background){return contrast(background,0xFFFFFF)>=contrast(background,0)?0xFFFFFF:0;}
    // The inspected engine calls 127 "WHITE100" and 255 "WHITE200".
    // Keep candidate channels at normal brightness; this does not attest texture/gamma output.
    public static int engineChannel(int srgb){if(srgb<0||srgb>255)throw new IllegalArgumentException("RGB channel required");return (srgb*127+127)/255;}
}
