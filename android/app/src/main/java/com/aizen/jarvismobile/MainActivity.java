package com.aizen.jarvismobile;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.MediaStore;
import android.provider.Settings;
import android.speech.RecognizerIntent;
import android.view.View;
import android.view.Window;
import android.webkit.HttpAuthHandler;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;

public class MainActivity extends Activity {
    private static final String HOST = "jarvis-mark-1-k6sq.onrender.com";
    private static final String HOME = "https://" + HOST + "/";
    private static final int SPEECH_REQUEST = 7101;
    private static final int AUDIO_PERMISSION = 7102;
    private static final String[] ALLOWED_APPS = {
            "calculator", "notepad", "file explorer", "paint", "spotify", "youtube",
            "youtube music", "gmail", "chrome", "maps", "google maps", "whatsapp",
            "instagram", "tiktok", "camera", "phone", "messages", "settings", "photos", "calendar"
    };
    private WebView webView;
    private String requestedApp;
    private long lastLaunchAt;
    private String lastLaunchApp = "";

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        Window window = getWindow();
        window.setStatusBarColor(android.graphics.Color.rgb(11, 17, 32));
        window.setNavigationBarColor(android.graphics.Color.rgb(11, 17, 32));
        getWindow().getDecorView().setSystemUiVisibility(0);
        webView = new WebView(this);
        webView.setBackgroundColor(android.graphics.Color.rgb(11, 17, 32));
        webView.getSettings().setJavaScriptEnabled(true);
        webView.getSettings().setDomStorageEnabled(true);
        webView.getSettings().setMediaPlaybackRequiresUserGesture(false);
        webView.getSettings().setAllowFileAccess(false);
        webView.getSettings().setAllowContentAccess(false);
        webView.addJavascriptInterface(new MobileBridge(), "JarvisMobile");
        webView.setWebChromeClient(new WebChromeClient());
        webView.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                if ("intent".equals(uri.getScheme())) {
                    launchApp(uri.getQueryParameter("app"));
                    return true;
                }
                if (HOST.equals(uri.getHost()) && "https".equals(uri.getScheme())) return false;
                if ("https".equals(uri.getScheme()) || "http".equals(uri.getScheme())) {
                    try { startActivity(new Intent(Intent.ACTION_VIEW, uri)); } catch (Exception ignored) {}
                }
                return true;
            }
            @Override public void onReceivedHttpAuthRequest(WebView view, HttpAuthHandler handler, String host, String realm) {
                if (!HOST.equals(host)) { handler.cancel(); return; }
                showLogin(handler);
            }
            @Override public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                if (!url.startsWith(HOME)) return;
                view.evaluateJavascript("(function(){var r=document.getElementById('reactor');if(!r||r.dataset.mobileMic)return;r.dataset.mobileMic='1';r.addEventListener('click',function(e){if(window.JarvisMobile){e.stopImmediatePropagation();window.JarvisMobile.listen();}},true);})();", null);
            }
        });
        setContentView(webView);
        Uri incoming = getIntent() == null ? null : getIntent().getData();
        if (incoming != null && "jarvismobile".equals(incoming.getScheme())) {
            launchApp(incoming.getQueryParameter("app"));
            finish();
        } else webView.loadUrl(HOME);
    }

    private void showLogin(HttpAuthHandler handler) {
        LinearLayout panel = new LinearLayout(this);
        panel.setPadding(48, 8, 48, 8);
        panel.setOrientation(LinearLayout.VERTICAL);
        TextView userLabel = new TextView(this); userLabel.setText("Username"); panel.addView(userLabel);
        EditText user = new EditText(this); user.setSingleLine(true); user.setText("jarvis"); panel.addView(user);
        TextView passLabel = new TextView(this); passLabel.setText("JARVIS website password"); panel.addView(passLabel);
        EditText pass = new EditText(this); pass.setSingleLine(true); pass.setInputType(129); panel.addView(pass);
        new AlertDialog.Builder(this).setTitle("Connect to J.A.R.V.I.S.").setMessage("Enter the password configured for your JARVIS website.").setView(panel)
                .setPositiveButton("Connect", (dialog, which) -> handler.proceed(user.getText().toString(), pass.getText().toString()))
                .setNegativeButton("Cancel", (dialog, which) -> handler.cancel()).setOnCancelListener(dialog -> handler.cancel()).show();
    }

    private class MobileBridge {
        @JavascriptInterface public void listen() {
            runOnUiThread(() -> {
                if (Build.VERSION.SDK_INT >= 23 && checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
                    requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, AUDIO_PERMISSION);
                    return;
                }
                startSpeechRecognition();
            });
        }
    }

    private void startSpeechRecognition() {
        try {
            Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault());
            intent.putExtra(RecognizerIntent.EXTRA_PROMPT, "Speak to JARVIS");
            startActivityForResult(intent, SPEECH_REQUEST);
        } catch (ActivityNotFoundException e) {
            Toast.makeText(this, "Speech recognition is unavailable on this device.", Toast.LENGTH_LONG).show();
        }
    }

    @Override public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == AUDIO_PERMISSION && grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) startSpeechRecognition();
        else if (requestCode == AUDIO_PERMISSION) Toast.makeText(this, "Allow microphone access to speak with JARVIS.", Toast.LENGTH_LONG).show();
    }

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == SPEECH_REQUEST && resultCode == RESULT_OK && data != null) {
            ArrayList<String> results = data.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS);
            if (results != null && !results.isEmpty()) {
                String text = results.get(0);
                String quoted = org.json.JSONObject.quote(text);
                webView.evaluateJavascript("(function(){var i=document.getElementById('typeBox'),f=document.getElementById('typeForm');if(i&&f){i.value=" + quoted + ";f.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));}})();", null);
            }
        }
    }

    private void launchApp(String rawName) {
        String app = rawName == null ? "" : rawName.toLowerCase(Locale.ROOT).trim();
        if (!Arrays.asList(ALLOWED_APPS).contains(app)) { Toast.makeText(this, "That app is not on JARVIS's launch list.", Toast.LENGTH_SHORT).show(); return; }
        long now = System.currentTimeMillis();
        if (app.equals(lastLaunchApp) && now - lastLaunchAt < 1800) return;
        lastLaunchAt = now; lastLaunchApp = app;
        try {
            Intent intent = appIntent(app);
            if (intent == null) throw new ActivityNotFoundException();
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(intent);
            if (webView != null && !isFinishing()) webView.evaluateJavascript("(function(){var s=document.getElementById('status');if(s)s.textContent=" + org.json.JSONObject.quote("Opened " + title(app) + ".") + ";})();", null);
        } catch (Exception e) {
            Toast.makeText(this, "Couldn't find " + title(app) + " on this phone.", Toast.LENGTH_LONG).show();
        }
    }

    private Intent appIntent(String app) {
        Map<String, String> packages = new HashMap<>();
        packages.put("calculator", "com.google.android.calculator"); packages.put("notepad", "com.google.android.keep");
        packages.put("paint", "com.microsoft.paint"); packages.put("spotify", "com.spotify.music");
        packages.put("youtube", "com.google.android.youtube"); packages.put("youtube music", "com.google.android.apps.youtube.music");
        packages.put("gmail", "com.google.android.gm"); packages.put("chrome", "com.android.chrome");
        packages.put("maps", "com.google.android.apps.maps"); packages.put("google maps", "com.google.android.apps.maps");
        packages.put("whatsapp", "com.whatsapp"); packages.put("instagram", "com.instagram.android");
        packages.put("tiktok", "com.zhiliaoapp.musically"); packages.put("photos", "com.google.android.apps.photos");
        packages.put("calendar", "com.google.android.calendar");
        if ("camera".equals(app)) return new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
        if ("phone".equals(app)) return new Intent(Intent.ACTION_DIAL);
        if ("messages".equals(app)) return new Intent(Intent.ACTION_SENDTO, Uri.parse("smsto:"));
        if ("settings".equals(app)) return new Intent(Settings.ACTION_SETTINGS);
        if ("file explorer".equals(app)) return new Intent(Intent.ACTION_OPEN_DOCUMENT).setType("*/*").addCategory(Intent.CATEGORY_OPENABLE);
        String pkg = packages.get(app);
        if (pkg == null) return null;
        Intent launch = getPackageManager().getLaunchIntentForPackage(pkg);
        if (launch != null) return launch;
        Intent market = new Intent(Intent.ACTION_VIEW, Uri.parse("market://details?id=" + pkg));
        if ("spotify".equals(app)) return market;
        return null;
    }

    private String title(String app) { return app.isEmpty() ? app : app.substring(0, 1).toUpperCase(Locale.ROOT) + app.substring(1); }
    @Override protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent); setIntent(intent);
        Uri data = intent.getData(); if (data != null) launchApp(data.getQueryParameter("app"));
    }
    @Override public void onBackPressed() {
        if (webView != null && webView.canGoBack()) webView.goBack(); else super.onBackPressed();
    }
    @Override protected void onDestroy() { if (webView != null) { webView.removeJavascriptInterface("JarvisMobile"); webView.destroy(); } super.onDestroy(); }
}

