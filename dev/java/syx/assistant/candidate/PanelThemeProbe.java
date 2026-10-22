package syx.assistant.candidate;
/** Offline authored palette/invalid-input checks; no game rendering or accessibility attestation. */
public final class PanelThemeProbe {
    private static void require(boolean b){if(!b)throw new AssertionError();}
    public static void main(String[] args){
        require(PanelTheme.preset("Forest").background==0x17251D);
        require(PanelTheme.preset("Parchment").bodyText==0);
        require(PanelTheme.preset("Night").bodyText==0xFFFFFF);
        for(String name:new String[]{"Forest","Parchment","Night"}){
            var t=PanelTheme.preset(name);require(PanelTheme.contrast(t.background,t.bodyText)>=4.5&&PanelTheme.contrast(t.accent,t.accentText)>=4.5);
        }
        for(String raw:new String[]{"", "#fff", "#00000000", "#gg0000", " abcdef", "abcdef\n", "0xabcdef", "#12345=", "#12\u0000345"}){
            try{PanelTheme.preset("Forest").withAccent(raw);throw new AssertionError("Malformed accent accepted");}catch(IllegalArgumentException expected){}
        }
        try{PanelTheme.preset("Forest").withAccent(null);throw new AssertionError();}catch(IllegalArgumentException expected){}
        try{PanelTheme.preset("forest");throw new AssertionError();}catch(IllegalArgumentException expected){}
        require(PanelTheme.preset("Forest").withAccent("abcdef").accentHex().equals("#ABCDEF"));
        require(PanelTheme.preset("Night").withAccent("#000000").accentText==0xFFFFFF);
        require(PanelTheme.preset("Night").withAccent("#FFFFFF").accentText==0);
        int cases=0;
        for(int r=0;r<=255;r+=17)for(int g=0;g<=255;g+=17)for(int b=0;b<=255;b+=17){
            var t=PanelTheme.preset("Forest").withAccent(String.format("#%02X%02X%02X",r,g,b));
            require(PanelTheme.contrast(t.accent,t.accentText)>=4.5);cases++;
        }
        require(cases==4096);require(PanelTheme.engineChannel(0)==0&&PanelTheme.engineChannel(255)==127);
        int last=-1;for(int i=0;i<=255;i++){int value=PanelTheme.engineChannel(i);require(value>=last&&value<=127);last=value;}
        for(int bad:new int[]{-1,256})try{PanelTheme.engineChannel(bad);throw new AssertionError();}catch(IllegalArgumentException expected){}
        System.out.println("PASS presets, strict accents, 4096 abstract contrast samples and engine-channel bounds");
    }
}
