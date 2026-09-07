package com.hes.osrsmini;

import android.app.Activity;
import android.app.ActivityOptions;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Rect;
import android.net.Uri;
import android.os.Bundle;
import android.provider.Settings;
import android.util.DisplayMetrics;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

public class MainActivity extends Activity {

    private static final String OSRS_PACKAGE = "com.jagex.oldscape.android";
    private TextView status;
    private boolean autoLaunchDone = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        buildUi();

        status.postDelayed(() -> {
            if (!autoLaunchDone) {
                autoLaunchDone = true;
                launchOsrsMini();
            }
        }, 250);
    }

    private void buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setGravity(Gravity.CENTER);
        int pad = dp(24);
        root.setPadding(pad, pad, pad, pad);

        TextView title = new TextView(this);
        title.setText("OSRS Mini");
        title.setTextSize(28f);
        title.setGravity(Gravity.CENTER);
        root.addView(title);

        status = new TextView(this);
        status.setText("OSRS wordt geopend als mini venster…");
        status.setTextSize(16f);
        status.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams statusParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        statusParams.setMargins(0, dp(18), 0, dp(18));
        root.addView(status, statusParams);

        Button open = new Button(this);
        open.setText("OPEN OSRS MINI");
        open.setOnClickListener(v -> launchOsrsMini());
        root.addView(open);

        Button settingsButton = new Button(this);
        settingsButton.setText("SAMSUNG INSTELLINGEN");
        settingsButton.setOnClickListener(v -> {
            try {
                startActivity(new Intent(Settings.ACTION_SETTINGS));
            } catch (Exception ignored) {
            }
        });
        LinearLayout.LayoutParams settingsParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        settingsParams.setMargins(0, dp(10), 0, 0);
        root.addView(settingsButton, settingsParams);

        setContentView(root);
    }

    private void launchOsrsMini() {
        PackageManager pm = getPackageManager();
        Intent intent = pm.getLaunchIntentForPackage(OSRS_PACKAGE);

        if (intent == null) {
            status.setText("OSRS is niet geïnstalleerd.");
            openPlayStore();
            return;
        }

        try {
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);

            ActivityOptions options = ActivityOptions.makeBasic();
            options.setLaunchBounds(calculateMiniBounds());

            startActivity(intent, options.toBundle());
            Toast.makeText(this, "OSRS Mini gestart", Toast.LENGTH_SHORT).show();
            finishAndRemoveTask();
        } catch (Exception e) {
            status.setText("Mini venster werd geblokkeerd. Zet op Samsung 'Multi window voor alle apps' aan bij Instellingen > Geavanceerde functies > Labs.");
        }
    }

    private Rect calculateMiniBounds() {
        DisplayMetrics metrics = new DisplayMetrics();
        getWindowManager().getDefaultDisplay().getRealMetrics(metrics);

        int screenW = metrics.widthPixels;
        int screenH = metrics.heightPixels;
        int margin = dp(18);

        int width;
        if (screenW < screenH) {
            width = (int) (screenW * 0.64f);
        } else {
            width = (int) (screenW * 0.46f);
        }

        int height = (int) (width * 0.5625f);
        int maxHeight = (int) (screenH * 0.55f);
        if (height > maxHeight) {
            height = maxHeight;
            width = (int) (height / 0.5625f);
        }

        int left = Math.max(margin, screenW - width - margin);
        int top = Math.max(margin, screenH - height - margin);
        int right = Math.min(screenW - margin, left + width);
        int bottom = Math.min(screenH - margin, top + height);

        return new Rect(left, top, right, bottom);
    }

    private void openPlayStore() {
        try {
            Intent market = new Intent(Intent.ACTION_VIEW,
                    Uri.parse("market://details?id=" + OSRS_PACKAGE));
            startActivity(market);
        } catch (Exception e) {
            Intent web = new Intent(Intent.ACTION_VIEW,
                    Uri.parse("https://play.google.com/store/apps/details?id=" + OSRS_PACKAGE));
            startActivity(web);
        }
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
