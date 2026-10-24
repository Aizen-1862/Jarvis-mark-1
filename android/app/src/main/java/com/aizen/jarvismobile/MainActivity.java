package com.aizen.jarvismobile;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.provider.MediaStore;
import android.provider.Settings;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

public final class MainActivity extends Activity {
    private static final int BG = Color.rgb(11, 17, 32);
    private static final int PANEL = Color.rgb(20, 30, 49);
    private static final int ACCENT = Color.rgb(56, 189, 248);
    private static final String[] COMMON_APPS = {
            "Calculator", "Spotify", "YouTube", "YouTube Music", "Gmail", "Chrome",
            "Maps", "WhatsApp", "Instagram", "TikTok", "Camera", "Phone",
            "Messages", "Settings", "Photos", "Calendar", "File Explorer", "Notepad", "Paint"
    };

    private TextView status;
    private String lastRequest = "";
    private long lastRequestAt;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        showHome();
        handleLaunch(getIntent());
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        handleLaunch(intent);
    }

    private void showHome() {
        ScrollView scroll = new ScrollView(this);
        scroll.setBackgroundColor(BG);
        LinearLayout page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        page.setPadding(dp(24), dp(36), dp(24), dp(28));
        scroll.addView(page);

        TextView title = new TextView(this);
        title.setText("J.A.R.V.I.S.");
        title.setTextColor(Color.WHITE);
        title.setTextSize(28);
        title.setGravity(Gravity.CENTER);
        page.addView(title, matchWrap());

        TextView subtitle = new TextView(this);
        subtitle.setText("Mobile app launcher");
        subtitle.setTextColor(ACCENT);
        subtitle.setTextSize(15);
        subtitle.setGravity(Gravity.CENTER);
        subtitle.setPadding(0, dp(4), 0, dp(18));
        page.addView(subtitle, matchWrap());

        TextView hint = new TextView(this);
        hint.setText("Tap an app, or send an app-opening request from the JARVIS website and tap its Open link.");
        hint.setTextColor(Color.rgb(203, 213, 225));
        hint.setTextSize(14);
        hint.setGravity(Gravity.CENTER);
        hint.setPadding(dp(14), dp(14), dp(14), dp(14));
        hint.setBackgroundColor(PANEL);
        page.addView(hint, matchWrap());

        status = new TextView(this);
        status.setText("Ready. App launches happen on this phone.");
        status.setTextColor(Color.rgb(148, 163, 184));
        status.setTextSize(13);
        status.setPadding(0, dp(14), 0, dp(10));
        page.addView(status, matchWrap());

        for (String app : COMMON_APPS) {
            Button button = new Button(this);
            button.setText("Open " + app);
            button.setTextColor(Color.WHITE);
            button.setAllCaps(false);
            button.setBackgroundTintList(android.content.res.ColorStateList.valueOf(PANEL));
            button.setOnClickListener(view -> launchApp(app));
            LinearLayout.LayoutParams params = matchWrap();
            params.topMargin = dp(7);
            page.addView(button, params);
        }
        setContentView(scroll);
    }

    private void handleLaunch(Intent intent) {
        if (intent == null || !Intent.ACTION_VIEW.equals(intent.getAction())) return;
        Uri uri = intent.getData();
        if (uri == null || !"jarvismobile".equals(uri.getScheme()) || !"launch".equals(uri.getHost())) return;
        String app = uri.getQueryParameter("app");
        if (app == null || app.length() > 40) {
            setStatus("JARVIS sent an invalid app name.");
            return;
        }
        launchApp(app);
    }

    private void launchApp(String requestedName) {
        String app = requestedName.trim().toLowerCase(Locale.ROOT);
        long now = System.currentTimeMillis();
        if (app.equals(lastRequest) && now - lastRequestAt < 1800) return;
        lastRequest = app;
        lastRequestAt = now;

        try {
            Intent launch = buildIntent(app);
            if (launch == null) {
                setStatus("That app is not on JARVIS Mobile's supported list yet.");
                return;
            }
            launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(launch);
            setStatus("Opened " + displayName(app) + ".");
        } catch (ActivityNotFoundException e) {
            setStatus(displayName(app) + " is not installed or Android could not open it.");
        } catch (SecurityException e) {
            setStatus("Android blocked that app launch.");
        }
    }

    private Intent buildIntent(String app) {
        switch (app) {
            case "camera":
                return new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
            case "phone":
                return new Intent(Intent.ACTION_DIAL);
            case "messages":
                return new Intent(Intent.ACTION_SENDTO, Uri.parse("smsto:"));
            case "settings":
                return new Intent(Settings.ACTION_SETTINGS);
            case "file explorer":
                return new Intent(Intent.ACTION_OPEN_DOCUMENT).setType("*/*").addCategory(Intent.CATEGORY_OPENABLE);
            default:
                List<String> packages = appPackages().get(app);
                if (packages == null) return null;
                for (String packageName : packages) {
                    Intent intent = getPackageManager().getLaunchIntentForPackage(packageName);
                    if (intent != null) return intent;
                }
                throw new ActivityNotFoundException(app);
        }
    }

    private Map<String, List<String>> appPackages() {
        Map<String, List<String>> map = new LinkedHashMap<>();
        map.put("calculator", Arrays.asList("com.google.android.calculator", "com.sec.android.app.popupcalculator", "com.android.calculator2"));
        map.put("notepad", Arrays.asList("com.google.android.keep"));
        map.put("paint", Arrays.asList("com.microsoft.paint"));
        map.put("spotify", Arrays.asList("com.spotify.music"));
        map.put("youtube", Arrays.asList("com.google.android.youtube"));
        map.put("youtube music", Arrays.asList("com.google.android.apps.youtube.music"));
        map.put("gmail", Arrays.asList("com.google.android.gm"));
        map.put("chrome", Arrays.asList("com.android.chrome"));
        map.put("maps", Arrays.asList("com.google.android.apps.maps"));
        map.put("google maps", Arrays.asList("com.google.android.apps.maps"));
        map.put("whatsapp", Arrays.asList("com.whatsapp"));
        map.put("instagram", Arrays.asList("com.instagram.android"));
        map.put("tiktok", Arrays.asList("com.zhiliaoapp.musically"));
        map.put("photos", Arrays.asList("com.google.android.apps.photos"));
        map.put("calendar", Arrays.asList("com.google.android.calendar"));
        return map;
    }

    private String displayName(String app) {
        if (app.isEmpty()) return app;
        return app.substring(0, 1).toUpperCase(Locale.ROOT) + app.substring(1);
    }

    private void setStatus(String message) {
        if (status != null) status.setText(message);
    }

    private LinearLayout.LayoutParams matchWrap() {
        return new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}

