from datetime import date

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from sqlalchemy import text
from app.database import engine
from app.intelligence.aging_rules import classify_status_with_default
from app.intelligence.danger_rules import calculate_age_in_days, danger_level

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


_DASHBOARD_HTML = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>SINDH Fashion Intelligence</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link
      href="https://fonts.googleapis.com/css2?family=Manrope:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap"
      rel="stylesheet"
    >
    <style>
      :root {
        --sage-400: #ACC82A;
        --olive-900: #1A2517;
        --ink-900: var(--olive-900);
        --ink-700: rgba(26, 37, 23, 0.82);
        --ink-500: rgba(26, 37, 23, 0.62);
        --sand-100: #f9fbf2;
        --sand-200: #f1f5e2;
        --mist-100: #edf2dc;
        --mint-400: var(--sage-400);
        --mint-600: var(--olive-900);
        --coral-500: var(--sage-400);
        --sun-400: var(--sage-400);
        --steel-400: rgba(26, 37, 23, 0.45);
        --white: #ffffff;
        --shadow: 0 20px 45px rgba(26, 37, 23, 0.18);
        --shadow-soft: 0 12px 28px rgba(26, 37, 23, 0.12);
        --radius-lg: 22px;
        --radius-md: 16px;
      }

      * {
        box-sizing: border-box;
      }

      body {
        margin: 0;
        min-height: 100vh;
        font-family: "Sora", "Noto Sans", sans-serif;
        color: var(--ink-900);
        background:
          radial-gradient(1100px 560px at 10% -10%, #f6f9e6 0, transparent 55%),
          radial-gradient(900px 520px at 110% 10%, #eef4d8 0, transparent 50%),
          linear-gradient(180deg, var(--sand-100) 0%, var(--mist-100) 100%);
        position: relative;
      }

      body::before {
        content: "";
        position: fixed;
        inset: 0;
        background-image:
          radial-gradient(rgba(26, 37, 23, 0.05) 1px, transparent 0),
          radial-gradient(rgba(26, 37, 23, 0.04) 1px, transparent 0);
        background-size: 22px 22px, 28px 28px;
        background-position: 0 0, 7px 9px;
        pointer-events: none;
        opacity: 0.6;
      }

      .page {
        position: relative;
        z-index: 1;
        padding: 32px 20px 60px;
        max-width: 1200px;
        margin: 0 auto;
      }

      header {
        display: flex;
        flex-wrap: wrap;
        gap: 16px;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 28px;
      }

      .title {
        display: grid;
        gap: 6px;
      }

      h1 {
        font-family: "Frances", "Georgia", serif;
        font-size: clamp(28px, 4vw, 40px);
        margin: 0;
        color: var(--ink-900);
      }

      .subtitle {
        color: var(--ink-500);
        font-size: 14px;
        letter-spacing: 0.4px;
        text-transform: uppercase;
      }

      .controls {
        display: flex;
        gap: 12px;
        align-items: center;
        flex-wrap: wrap;
      }

      .chip {
        background: rgba(255, 255, 255, 0.8);
        border: 1px solid rgba(26, 37, 23, 0.18);
        padding: 10px 16px;
        border-radius: 999px;
        font-size: 13px;
        color: var(--ink-700);
        box-shadow: var(--shadow-soft);
      }

      .button {
        border: none;
        padding: 12px 18px;
        border-radius: 999px;
        background: var(--sage-400);
        color: var(--olive-900);
        font-weight: 600;
        cursor: pointer;
        box-shadow: var(--shadow-soft);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
      }

      .button:hover {
        transform: translateY(-1px);
        box-shadow: var(--shadow);
      }

      .button-outline {
        background: var(--white);
        color: var(--ink-900);
        border: 1px solid rgba(26, 37, 23, 0.24);
      }

      .grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 18px;
        margin-bottom: 28px;
      }

      .card {
        background: rgba(255, 255, 255, 0.92);
        border-radius: var(--radius-lg);
        padding: 20px 22px;
        box-shadow: var(--shadow);
        border: 1px solid rgba(26, 37, 23, 0.12);
        animation: floatUp 0.7s ease both;
        animation-delay: var(--delay, 0ms);
      }

      .card h2 {
        margin: 0 0 6px 0;
        font-size: 14px;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        color: var(--ink-500);
      }

      .card .value {
        font-size: clamp(22px, 3vw, 28px);
        font-weight: 600;
      }

      .card .note {
        margin-top: 8px;
        font-size: 13px;
        color: var(--ink-500);
      }

      .section {
        display: grid;
        gap: 16px;
      }

      .panel {
        background: rgba(255, 255, 255, 0.94);
        border-radius: var(--radius-lg);
        padding: 18px 20px 6px;
        box-shadow: var(--shadow);
        border: 1px solid rgba(26, 37, 23, 0.12);
      }

      .panel header {
        margin-bottom: 14px;
      }

      .panel-title {
        font-family: "Frances", "Georgia", serif;
        font-size: 20px;
        margin: 0;
      }

      .panel-sub {
        color: var(--ink-500);
        margin-top: 4px;
        font-size: 13px;
      }

      table {
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
      }

      thead th {
        text-align: left;
        padding: 12px 10px;
        font-size: 12px;
        letter-spacing: 0.6px;
        text-transform: uppercase;
        color: var(--ink-500);
        border-bottom: 1px solid rgba(26, 37, 23, 0.2);
      }

      tbody td {
        padding: 12px 10px;
        border-bottom: 1px solid rgba(26, 37, 23, 0.12);
      }

      tbody tr:hover {
        background: rgba(172, 200, 42, 0.12);
      }

      .store-id {
        font-weight: 600;
        color: var(--ink-700);
      }

      .pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 600;
        margin-right: 6px;
      }

      .pill.early {
        background: rgba(172, 200, 42, 0.2);
        color: var(--olive-900);
      }

      .pill.high {
        background: rgba(172, 200, 42, 0.35);
        color: var(--olive-900);
      }

      .pill.critical {
        background: var(--olive-900);
        color: var(--sand-100);
      }

      .pill.none {
        background: rgba(26, 37, 23, 0.08);
        color: var(--ink-700);
      }

      .pill.healthy {
        background: rgba(172, 200, 42, 0.18);
        color: var(--olive-900);
      }

      .pill.transfer {
        background: rgba(172, 200, 42, 0.32);
        color: var(--olive-900);
      }

      .pill.rr-tt {
        background: rgba(26, 37, 23, 0.16);
        color: var(--olive-900);
      }

      .pill.very-danger {
        background: var(--olive-900);
        color: var(--sand-100);
      }

      .pill.unknown {
        background: rgba(26, 37, 23, 0.08);
        color: var(--ink-700);
      }

      .search {
        display: flex;
        gap: 10px;
        align-items: center;
        flex-wrap: wrap;
      }

      .search-block {
        display: grid;
        gap: 10px;
        justify-items: end;
      }

      .search-input {
        border: 1px solid rgba(26, 37, 23, 0.24);
        border-radius: 999px;
        padding: 10px 14px;
        font-size: 13px;
        min-width: 220px;
        background: var(--white);
        color: var(--ink-900);
      }

      .filter-row {
        display: flex;
        flex-wrap: wrap;
        gap: 8px 12px;
        align-items: center;
        justify-content: flex-end;
      }

      .filter-label {
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 0.6px;
        text-transform: uppercase;
        color: var(--ink-500);
      }

      .chip-row {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        align-items: center;
      }

      button.chip {
        font-family: inherit;
      }

      .chip.toggle {
        cursor: pointer;
        transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease, color 0.2s ease;
      }

      .chip.toggle:hover {
        transform: translateY(-1px);
        box-shadow: var(--shadow-soft);
      }

      .chip.toggle.active {
        background: var(--sage-400);
        color: var(--olive-900);
        border-color: rgba(26, 37, 23, 0.32);
      }

      .chip.clear {
        background: rgba(255, 255, 255, 0.6);
        border-style: dashed;
      }

      .chip.clear:hover {
        background: rgba(255, 255, 255, 0.9);
      }

      .total {
        font-weight: 600;
        color: var(--ink-900);
      }

      .status {
        margin-top: 12px;
        font-size: 13px;
        color: var(--ink-500);
      }

      .empty {
        padding: 24px;
        text-align: center;
        color: var(--ink-500);
      }

      :root {
        --bg-950: #0b0f1a;
        --bg-900: #0e1425;
        --bg-850: #121a2f;
        --glass-100: rgba(255, 255, 255, 0.08);
        --glass-200: rgba(255, 255, 255, 0.12);
        --glass-300: rgba(255, 255, 255, 0.18);
        --stroke-100: rgba(255, 255, 255, 0.14);
        --stroke-200: rgba(255, 255, 255, 0.22);
        --text-100: #f2f5ff;
        --text-200: rgba(242, 245, 255, 0.78);
        --text-300: rgba(242, 245, 255, 0.6);
        --text-400: rgba(242, 245, 255, 0.42);
        --blue-400: #4ca7ff;
        --cyan-400: #39f0ff;
        --violet-400: #8d7bff;
        --violet-500: #6c5cff;
        --shadow-lg: 0 30px 60px rgba(5, 9, 25, 0.55);
        --shadow-md: 0 16px 32px rgba(8, 12, 28, 0.45);
      }

      body {
        font-family: "Manrope", "Space Grotesk", sans-serif;
        color: var(--text-100);
        background:
          radial-gradient(1200px 600px at 5% -10%, rgba(76, 167, 255, 0.25), transparent 60%),
          radial-gradient(900px 520px at 110% 10%, rgba(141, 123, 255, 0.22), transparent 55%),
          radial-gradient(900px 520px at 40% 120%, rgba(57, 240, 255, 0.18), transparent 55%),
          linear-gradient(180deg, var(--bg-900) 0%, var(--bg-950) 100%);
      }

      body::before {
        background-image:
          radial-gradient(rgba(255, 255, 255, 0.06) 1px, transparent 0),
          radial-gradient(rgba(255, 255, 255, 0.04) 1px, transparent 0);
        background-size: 28px 28px, 42px 42px;
        background-position: 0 0, 12px 18px;
        opacity: 0.4;
      }

      .shell {
        max-width: 1400px;
        margin: 0 auto;
        padding: 24px;
        display: grid;
        grid-template-columns: 92px minmax(0, 1fr);
        gap: 24px;
      }

      button {
        font-family: inherit;
        color: inherit;
        background: none;
        border: none;
        padding: 0;
      }

      .glass {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.12), rgba(255, 255, 255, 0.04));
        border: 1px solid var(--stroke-100);
        box-shadow: var(--shadow-lg);
        backdrop-filter: blur(18px);
        -webkit-backdrop-filter: blur(18px);
      }

      .sidebar {
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        padding: 18px 14px;
        border-radius: 28px;
        position: sticky;
        top: 24px;
        height: calc(100vh - 48px);
      }

      .brand-text {
        font-size: 10px;
        letter-spacing: 1px;
        text-transform: uppercase;
        color: var(--text-300);
      }

      .logo {
        width: 46px;
        height: 46px;
        border-radius: 16px;
        background:
          radial-gradient(circle at 30% 30%, rgba(57, 240, 255, 0.9), transparent 60%),
          linear-gradient(135deg, rgba(76, 167, 255, 0.8), rgba(141, 123, 255, 0.8));
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: "Space Grotesk", sans-serif;
        font-weight: 600;
        font-size: 14px;
        color: #0b0f1a;
        box-shadow: 0 0 20px rgba(57, 240, 255, 0.45);
      }

      .nav {
        display: flex;
        flex-direction: column;
        gap: 12px;
        margin-top: 18px;
      }

      .nav-icon {
        width: 52px;
        height: 52px;
        border-radius: 16px;
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.12);
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--text-200);
        transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease, color 0.2s ease;
      }

      .nav-icon svg {
        width: 22px;
        height: 22px;
        stroke: currentColor;
        stroke-linecap: round;
        stroke-linejoin: round;
      }

      .nav-icon.active {
        background: rgba(57, 240, 255, 0.14);
        color: var(--cyan-400);
        box-shadow: 0 0 18px rgba(57, 240, 255, 0.35);
      }

      .nav-icon:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 24px rgba(8, 12, 26, 0.5);
      }

      .sidebar-footer {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        font-size: 11px;
        color: var(--text-300);
      }

      .live-dot {
        width: 8px;
        height: 8px;
        border-radius: 999px;
        background: var(--cyan-400);
        box-shadow: 0 0 12px rgba(57, 240, 255, 0.8);
        animation: pulse 2.2s infinite;
      }

      .page {
        max-width: none;
        margin: 0;
        padding: 12px 0 60px;
      }

      header {
        margin-bottom: 24px;
      }

      .title {
        gap: 8px;
      }

      h1 {
        font-family: "Space Grotesk", sans-serif;
        color: var(--text-100);
      }

      .subtitle {
        color: var(--text-300);
      }

      .subtitle.tagline {
        text-transform: none;
        letter-spacing: 0;
        font-size: 13px;
        color: var(--text-200);
      }

      .controls {
        gap: 12px;
        align-items: center;
        justify-content: flex-end;
      }

      .chip {
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.16);
        color: var(--text-200);
        box-shadow: var(--shadow-md);
        display: inline-flex;
        align-items: center;
        gap: 8px;
      }

      .chip.tag {
        border-color: rgba(76, 167, 255, 0.35);
      }

      .live-chip {
        cursor: pointer;
        transition: box-shadow 0.2s ease;
      }

      .live-chip:hover {
        box-shadow: 0 0 16px rgba(57, 240, 255, 0.35);
      }

      .live-chip.off {
        opacity: 0.6;
      }

      .live-chip.off .live-dot {
        animation: none;
        background: var(--text-400);
        box-shadow: none;
      }

      .action-dock {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
        justify-content: flex-end;
      }

      .action-pill {
        --accent: var(--cyan-400);
        --glow: rgba(57, 240, 255, 0.35);
        position: relative;
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px 14px;
        border-radius: 999px;
        background: rgba(16, 22, 36, 0.65);
        border: 1px solid rgba(255, 255, 255, 0.14);
        color: var(--text-200);
        width: 52px;
        overflow: hidden;
        cursor: pointer;
        transition: width 0.25s ease, box-shadow 0.25s ease, background 0.25s ease, transform 0.2s ease;
      }

      .action-pill[data-accent="blue"] {
        --accent: var(--blue-400);
        --glow: rgba(76, 167, 255, 0.35);
      }

      .action-pill[data-accent="violet"] {
        --accent: var(--violet-400);
        --glow: rgba(141, 123, 255, 0.35);
      }

      .action-pill[data-accent="ice"] {
        --accent: #7ee7ff;
        --glow: rgba(126, 231, 255, 0.4);
      }

      .action-pill::after {
        content: "";
        position: absolute;
        inset: 0;
        border-radius: 999px;
        background: linear-gradient(90deg, rgba(255, 255, 255, 0.15), transparent 70%);
        opacity: 0;
        transition: opacity 0.25s ease;
      }

      .action-pill:hover,
      .action-pill.active {
        width: 190px;
        background: rgba(26, 34, 52, 0.85);
        box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.22), 0 0 22px var(--glow);
        transform: translateY(-1px);
      }

      .action-pill:hover::after,
      .action-pill.active::after {
        opacity: 1;
      }

      .action-pill.clicked {
        animation: actionFlash 0.6s ease;
      }

      .action-icon {
        width: 18px;
        height: 18px;
        stroke: var(--accent);
        filter: drop-shadow(0 0 6px var(--glow));
        flex-shrink: 0;
        stroke-linecap: round;
        stroke-linejoin: round;
      }

      .action-text {
        display: flex;
        flex-direction: column;
        gap: 2px;
        opacity: 0;
        transform: translateX(-6px);
        transition: opacity 0.2s ease, transform 0.2s ease;
      }

      .action-title {
        white-space: nowrap;
        font-size: 12px;
        letter-spacing: 0.3px;
      }

      .action-sub {
        font-size: 10px;
        color: var(--text-300);
      }

      .action-pill:hover .action-text,
      .action-pill.active .action-text {
        opacity: 1;
        transform: translateX(0);
      }

      .grid {
        margin-bottom: 24px;
      }

      .card {
        background: rgba(12, 18, 32, 0.78);
        border: 1px solid rgba(255, 255, 255, 0.12);
        box-shadow: var(--shadow-lg);
      }

      .card h2 {
        color: var(--text-300);
      }

      .card .value {
        color: var(--text-100);
      }

      .card .note {
        color: var(--text-300);
      }

      .section {
        gap: 18px;
      }

      .analytics-grid {
        display: grid;
        grid-template-columns: minmax(0, 2fr) minmax(0, 1fr);
        gap: 18px;
      }

      .panel-title {
        font-family: "Space Grotesk", sans-serif;
        color: var(--text-100);
      }

      .panel-sub {
        color: var(--text-300);
      }

      .panel {
        background: rgba(12, 18, 32, 0.78);
        border: 1px solid rgba(255, 255, 255, 0.12);
        box-shadow: var(--shadow-lg);
        backdrop-filter: blur(18px);
        -webkit-backdrop-filter: blur(18px);
      }

      .chart-area {
        position: relative;
        height: 240px;
        border-radius: var(--radius-md);
        background: rgba(10, 14, 24, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.08);
        overflow: hidden;
        margin-bottom: 16px;
      }

      .chart-area::before {
        content: "";
        position: absolute;
        inset: 0;
        background-image:
          linear-gradient(transparent 70%, rgba(255, 255, 255, 0.04)),
          linear-gradient(90deg, rgba(255, 255, 255, 0.04) 1px, transparent 1px);
        background-size: 100% 40px, 60px 100%;
        opacity: 0.35;
        pointer-events: none;
      }

      .trend-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 12px;
      }

      .trend-card {
        background: rgba(12, 18, 32, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 14px;
        padding: 12px;
        display: grid;
        gap: 6px;
        color: var(--text-300);
      }

      .trend-label {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.8px;
      }

      .trend-value {
        font-size: 18px;
        font-weight: 600;
        color: var(--text-100);
      }

      .trend-value.positive {
        color: var(--cyan-400);
      }

      .trend-value.neutral {
        color: var(--violet-400);
      }

      .health-grid {
        display: grid;
        gap: 14px;
      }

      .health-item {
        display: grid;
        gap: 6px;
        font-size: 12px;
        color: var(--text-300);
      }

      .health-row {
        display: flex;
        justify-content: space-between;
      }

      .health-value {
        font-weight: 600;
        color: var(--text-100);
      }

      .health-bar {
        height: 6px;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.08);
        overflow: hidden;
      }

      .health-bar span {
        display: block;
        height: 100%;
        background: linear-gradient(90deg, var(--cyan-400), var(--violet-400));
        box-shadow: 0 0 12px rgba(57, 240, 255, 0.4);
      }

      .health-insights {
        margin-top: 16px;
        display: grid;
        gap: 10px;
        font-size: 12px;
        color: var(--text-300);
      }

      .health-insight {
        display: flex;
        justify-content: space-between;
      }

      .search-panel.filters-open {
        box-shadow: 0 0 0 1px rgba(57, 240, 255, 0.4), 0 0 28px rgba(57, 240, 255, 0.35);
      }

      table {
        color: var(--text-200);
      }

      thead th {
        color: var(--text-300);
        border-bottom: 1px solid rgba(255, 255, 255, 0.12);
      }

      tbody td {
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      }

      tbody tr:hover {
        background: rgba(76, 167, 255, 0.08);
      }

      .store-id,
      .total {
        color: var(--text-100);
      }

      .status,
      .empty,
      .filter-label {
        color: var(--text-300);
      }

      .chip.toggle.active {
        background: rgba(57, 240, 255, 0.16);
        color: var(--text-100);
        border-color: rgba(57, 240, 255, 0.45);
        box-shadow: 0 0 12px rgba(57, 240, 255, 0.25);
      }

      .chip.toggle:hover {
        box-shadow: 0 0 12px rgba(57, 240, 255, 0.18);
      }

      .chip.clear {
        background: rgba(255, 255, 255, 0.04);
        border-style: dashed;
        border-color: rgba(255, 255, 255, 0.18);
        color: var(--text-300);
      }

      .chip.clear:hover {
        background: rgba(255, 255, 255, 0.12);
      }

      .pill {
        border: 1px solid rgba(255, 255, 255, 0.18);
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 0.4px;
      }

      .pill.early {
        background: rgba(76, 167, 255, 0.18);
        color: var(--blue-400);
      }

      .pill.high {
        background: rgba(141, 123, 255, 0.18);
        color: var(--violet-400);
      }

      .pill.critical {
        background: rgba(57, 240, 255, 0.2);
        color: var(--cyan-400);
      }

      .pill.healthy {
        background: rgba(76, 167, 255, 0.16);
        color: var(--blue-400);
      }

      .pill.transfer {
        background: rgba(57, 240, 255, 0.16);
        color: var(--cyan-400);
      }

      .pill.rr-tt {
        background: rgba(141, 123, 255, 0.16);
        color: var(--violet-400);
      }

      .pill.very-danger {
        background: rgba(108, 92, 255, 0.24);
        color: var(--violet-500);
      }

      .pill.none,
      .pill.unknown {
        background: rgba(255, 255, 255, 0.08);
        color: var(--text-300);
      }

      .button {
        background: rgba(16, 22, 36, 0.7);
        color: var(--text-100);
        border: 1px solid rgba(255, 255, 255, 0.18);
      }

      .button-outline {
        background: transparent;
        color: var(--text-100);
        border-color: rgba(255, 255, 255, 0.22);
      }

      .search-input {
        background: rgba(10, 14, 24, 0.6);
        color: var(--text-100);
        border: 1px solid rgba(255, 255, 255, 0.2);
      }

      .search-input:focus {
        border-color: var(--cyan-400);
        box-shadow: 0 0 0 2px rgba(57, 240, 255, 0.2);
      }

      .toast {
        position: fixed;
        right: 24px;
        bottom: 24px;
        padding: 12px 16px;
        border-radius: 14px;
        background: rgba(12, 18, 32, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.18);
        color: var(--text-100);
        font-size: 12px;
        opacity: 0;
        transform: translateY(10px);
        transition: opacity 0.3s ease, transform 0.3s ease;
        pointer-events: none;
        box-shadow: var(--shadow-md);
      }

      .toast.show {
        opacity: 1;
        transform: translateY(0);
      }

      .toast.success {
        border-color: rgba(57, 240, 255, 0.4);
        box-shadow: 0 0 18px rgba(57, 240, 255, 0.35);
      }

      @keyframes pulse {
        0% {
          transform: scale(1);
          opacity: 0.9;
        }
        70% {
          transform: scale(1.6);
          opacity: 0;
        }
        100% {
          transform: scale(1);
          opacity: 0;
        }
      }

      @keyframes actionFlash {
        0% {
          box-shadow: 0 0 0 rgba(57, 240, 255, 0.0);
        }
        50% {
          box-shadow: 0 0 24px rgba(57, 240, 255, 0.4);
        }
        100% {
          box-shadow: 0 0 0 rgba(57, 240, 255, 0.0);
        }
      }

      @keyframes floatUp {
        from { opacity: 0; transform: translateY(12px); }
        to { opacity: 1; transform: translateY(0); }
      }

      @media (max-width: 1100px) {
        .analytics-grid {
          grid-template-columns: 1fr;
        }
      }

      @media (max-width: 980px) {
        .shell {
          grid-template-columns: 1fr;
        }
        .sidebar {
          position: relative;
          height: auto;
          flex-direction: row;
          align-items: center;
          gap: 18px;
        }
        .nav {
          flex-direction: row;
          margin-top: 0;
          flex-wrap: wrap;
        }
        .sidebar-footer {
          margin-left: auto;
        }
      }

      @media (max-width: 680px) {
        header {
          flex-direction: column;
          align-items: flex-start;
        }
        .controls {
          width: 100%;
          justify-content: space-between;
        }
        .search {
          width: 100%;
        }
        .search-block {
          width: 100%;
          justify-items: stretch;
        }
        .search-input {
          width: 100%;
        }
        .action-dock {
          width: 100%;
        }
        .action-pill,
        .action-pill:hover,
        .action-pill.active {
          width: 100%;
        }
        .action-text {
          opacity: 1;
          transform: none;
        }
        .filter-row {
          justify-content: flex-start;
        }
        table, thead, tbody, th, td, tr {
          display: block;
        }
        thead {
          display: none;
        }
        tbody tr {
          margin-bottom: 16px;
          border-radius: var(--radius-md);
          background: rgba(12, 18, 32, 0.78);
          border: 1px solid rgba(255, 255, 255, 0.12);
          box-shadow: var(--shadow-md);
        }
        tbody td {
          border: none;
          padding: 10px 14px;
          display: flex;
          justify-content: space-between;
        }
        tbody td::before {
          content: attr(data-label);
          color: var(--text-400);
          font-size: 12px;
          text-transform: uppercase;
          letter-spacing: 0.4px;
        }
      }
    </style>
  </head>
  <body>
    <div class="shell">
      <aside class="sidebar glass">
        <div class="brand">
          <div class="logo">SF</div>
          <div class="brand-text">SINDH FASHION</div>
        </div>
        <nav class="nav">
          <button class="nav-icon active" type="button" aria-label="Overview">
            <svg viewBox="0 0 24 24" fill="none" stroke-width="1.6">
              <rect x="3.5" y="3.5" width="7" height="7" rx="1.5"></rect>
              <rect x="13.5" y="3.5" width="7" height="7" rx="1.5"></rect>
              <rect x="3.5" y="13.5" width="7" height="7" rx="1.5"></rect>
              <rect x="13.5" y="13.5" width="7" height="7" rx="1.5"></rect>
            </svg>
          </button>
          <button class="nav-icon" type="button" aria-label="Analytics">
            <svg viewBox="0 0 24 24" fill="none" stroke-width="1.6">
              <path d="M4 19h16"></path>
              <path d="M6 16l4-5 4 3 4-6"></path>
              <circle cx="6" cy="16" r="1"></circle>
              <circle cx="10" cy="11" r="1"></circle>
              <circle cx="14" cy="14" r="1"></circle>
              <circle cx="18" cy="8" r="1"></circle>
            </svg>
          </button>
          <button class="nav-icon" type="button" aria-label="Automation">
            <svg viewBox="0 0 24 24" fill="none" stroke-width="1.6">
              <path d="M12 3v4"></path>
              <path d="M12 17v4"></path>
              <path d="M4.9 7.2l2.8 2.8"></path>
              <path d="M16.3 14.6l2.8 2.8"></path>
              <path d="M3 12h4"></path>
              <path d="M17 12h4"></path>
              <path d="M4.9 16.8l2.8-2.8"></path>
              <path d="M16.3 9.4l2.8-2.8"></path>
              <circle cx="12" cy="12" r="3"></circle>
            </svg>
          </button>
          <button class="nav-icon" type="button" aria-label="Reports">
            <svg viewBox="0 0 24 24" fill="none" stroke-width="1.6">
              <path d="M7 3h7l5 5v13a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z"></path>
              <path d="M14 3v5h5"></path>
              <path d="M9 14h6"></path>
              <path d="M9 17h6"></path>
            </svg>
          </button>
          <button class="nav-icon" type="button" aria-label="Settings">
            <svg viewBox="0 0 24 24" fill="none" stroke-width="1.6">
              <circle cx="12" cy="12" r="3.2"></circle>
              <path d="M19 12l2 0"></path>
              <path d="M3 12l2 0"></path>
              <path d="M12 3l0 2"></path>
              <path d="M12 19l0 2"></path>
              <path d="M17.2 6.8l1.4-1.4"></path>
              <path d="M5.4 18.6l1.4-1.4"></path>
              <path d="M6.8 6.8l-1.4-1.4"></path>
              <path d="M18.6 18.6l-1.4-1.4"></path>
            </svg>
          </button>
        </nav>
        <div class="sidebar-footer">
          <span class="live-dot"></span>
          <span>System Live</span>
        </div>
      </aside>
      <main class="page">
      <header>
        <div class="title">
          <div class="subtitle">SINDH FASHION</div>
          <h1>System Intelligence</h1>
          <div class="subtitle tagline">Real-time data, automation insights, and system intelligence.</div>
        </div>
        <div class="controls">
          <button class="chip live-chip" id="live-toggle" type="button" aria-pressed="true">
            <span class="live-dot"></span>
            <span>Live Sync</span>
          </button>
          <div class="chip" id="as-of">As of --</div>
          <div class="action-dock">
            <button class="action-pill" id="refresh" type="button" data-action="refresh" data-accent="cyan">
              <svg class="action-icon" viewBox="0 0 24 24" fill="none" stroke-width="1.6">
                <path d="M4 12a8 8 0 0 1 13.66-5.66"></path>
                <path d="M20 4v6h-6"></path>
                <path d="M20 12a8 8 0 0 1-13.66 5.66"></path>
                <path d="M4 20v-6h6"></path>
              </svg>
              <span class="action-text">
                <span class="action-title">Refresh Live</span>
                <span class="action-sub">Sync data</span>
              </span>
            </button>
            <button class="action-pill" id="export-report" type="button" data-action="export" data-accent="blue">
              <svg class="action-icon" viewBox="0 0 24 24" fill="none" stroke-width="1.6">
                <path d="M12 3v12"></path>
                <path d="M8 11l4 4 4-4"></path>
                <path d="M4 20h16"></path>
              </svg>
              <span class="action-text">
                <span class="action-title">Export Report</span>
                <span class="action-sub">CSV snapshot</span>
              </span>
            </button>
            <button class="action-pill" id="filter-toggle" type="button" data-action="filters" data-accent="ice">
              <svg class="action-icon" viewBox="0 0 24 24" fill="none" stroke-width="1.6">
                <path d="M3 5h18"></path>
                <path d="M6 12h12"></path>
                <path d="M10 19h4"></path>
              </svg>
              <span class="action-text">
                <span class="action-title">Apply Filters</span>
                <span class="action-sub">Departments</span>
              </span>
            </button>
            <button class="action-pill" id="automation-trigger" type="button" data-action="automate" data-accent="violet">
              <svg class="action-icon" viewBox="0 0 24 24" fill="none" stroke-width="1.6">
                <path d="M13 2L6 14h6l-1 8 7-12h-6l1-8z"></path>
              </svg>
              <span class="action-text">
                <span class="action-title">Trigger Auto</span>
                <span class="action-sub">Run workflows</span>
              </span>
            </button>
          </div>
        </div>
      </header>

      <section class="grid">
        <div class="card" style="--delay: 0ms;">
          <h2>Total Danger Capital</h2>
          <div class="value" id="summary-total">INR --</div>
          <div class="note">Only EARLY, HIGH, CRITICAL inventory</div>
        </div>
        <div class="card" style="--delay: 120ms;">
          <h2>Stores in Alert Zone</h2>
          <div class="value" id="summary-count">--</div>
          <div class="note">Stores with any alert-visible stock</div>
        </div>
        <div class="card" style="--delay: 240ms;">
          <h2>Most Exposed Store</h2>
          <div class="value" id="summary-top">--</div>
          <div class="note" id="summary-top-note">Waiting for data</div>
        </div>
        <div class="card" style="--delay: 360ms;">
          <h2>API Latency</h2>
          <div class="value" id="summary-latency">-- ms</div>
          <div class="note">Live response window</div>
        </div>
      </section>

      <section class="section">
        <div class="analytics-grid">
          <div class="panel analytics-panel">
            <header>
              <div>
                <h3 class="panel-title">Real-time Analytics</h3>
                <div class="panel-sub">Exposure trends and automation flow.</div>
              </div>
              <div class="chip-row">
                <span class="chip tag">Live</span>
                <span class="chip tag">Predictive</span>
              </div>
            </header>
            <div class="chart-area">
              <svg viewBox="0 0 800 240" preserveAspectRatio="none">
                <defs>
                  <linearGradient id="lineGlow" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stop-color="#39f0ff" stop-opacity="0.1" />
                    <stop offset="50%" stop-color="#4ca7ff" stop-opacity="0.6" />
                    <stop offset="100%" stop-color="#8d7bff" stop-opacity="0.9" />
                  </linearGradient>
                  <linearGradient id="fillGlow" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#39f0ff" stop-opacity="0.25" />
                    <stop offset="100%" stop-color="#0b0f1a" stop-opacity="0" />
                  </linearGradient>
                </defs>
                <path
                  d="M0 180 C 80 140, 160 160, 240 120 C 320 80, 400 120, 480 90 C 560 60, 640 80, 720 50 C 760 35, 780 40, 800 38"
                  fill="none"
                  stroke="url(#lineGlow)"
                  stroke-width="3"
                />
                <path
                  d="M0 180 C 80 140, 160 160, 240 120 C 320 80, 400 120, 480 90 C 560 60, 640 80, 720 50 C 760 35, 780 40, 800 38 L 800 240 L 0 240 Z"
                  fill="url(#fillGlow)"
                  stroke="none"
                />
                <path
                  d="M0 200 C 100 170, 200 190, 300 150 C 400 110, 500 140, 600 110 C 700 80, 760 95, 800 90"
                  fill="none"
                  stroke="rgba(57, 240, 255, 0.4)"
                  stroke-width="2"
                  stroke-dasharray="6 6"
                />
              </svg>
            </div>
            <div class="trend-grid">
              <div class="trend-card">
                <span class="trend-label">Risk Velocity</span>
                <span class="trend-value positive">+8.2%</span>
              </div>
              <div class="trend-card">
                <span class="trend-label">Automation Coverage</span>
                <span class="trend-value neutral">74%</span>
              </div>
              <div class="trend-card">
                <span class="trend-label">Forecast Stability</span>
                <span class="trend-value">Stable</span>
              </div>
            </div>
          </div>
          <div class="panel health-panel">
            <header>
              <div>
                <h3 class="panel-title">System Health</h3>
                <div class="panel-sub">Live signals across pipeline and automation.</div>
              </div>
            </header>
            <div class="health-grid">
              <div class="health-item">
                <div class="health-row">
                  <span>API Latency</span>
                  <span class="health-value" id="health-latency">-- ms</span>
                </div>
                <div class="health-bar"><span id="health-latency-bar" style="width: 50%;"></span></div>
              </div>
              <div class="health-item">
                <div class="health-row">
                  <span>Ingestion Pipeline</span>
                  <span class="health-value" id="health-ingest">Stable</span>
                </div>
                <div class="health-bar"><span id="health-ingest-bar" style="width: 86%;"></span></div>
              </div>
              <div class="health-item">
                <div class="health-row">
                  <span>Automation Queue</span>
                  <span class="health-value" id="health-automation">0 queued</span>
                </div>
                <div class="health-bar"><span id="health-automation-bar" style="width: 42%;"></span></div>
              </div>
            </div>
            <div class="health-insights">
              <div class="health-insight">
                <span>Workflow Engine</span>
                <span id="automation-count">0 runs today</span>
              </div>
              <div class="health-insight">
                <span>Last Automation</span>
                <span id="automation-latest">--</span>
              </div>
              <div class="health-insight">
                <span>Alert Pipeline</span>
                <span>Online</span>
              </div>
            </div>
          </div>
        </div>
        <div class="panel">
          <header>
            <div>
              <h3 class="panel-title">Store Breakdown</h3>
              <div class="panel-sub">Capital by danger tier, sorted by total exposure.</div>
            </div>
          </header>

          <table>
            <thead>
              <tr>
                <th>Store</th>
                <th>Early</th>
                <th>High</th>
                <th>Critical</th>
                <th>Total</th>
              </tr>
            </thead>
            <tbody id="store-rows">
              <tr><td class="empty" colspan="5">Loading data...</td></tr>
            </tbody>
          </table>
          <div class="status" id="status">Fetching latest data.</div>
        </div>

        <div class="panel">
          <header>
            <div>
              <h3 class="panel-title">Aging Status Summary</h3>
              <div class="panel-sub">Capital by aging status across all inventory.</div>
            </div>
            <div class="search">
              <input class="search-input" id="aging-search-input" placeholder="Filter by store ID" />
              <button class="button button-outline" id="aging-search-button">Filter</button>
            </div>
          </header>

          <table>
            <thead>
              <tr>
                <th>Store</th>
                <th>Healthy</th>
                <th>Transfer</th>
                <th>RR_TT</th>
                <th>VERY_DANGER</th>
                <th>Total</th>
              </tr>
            </thead>
            <tbody id="aging-rows">
              <tr><td class="empty" colspan="6">Loading data...</td></tr>
            </tbody>
          </table>
          <div class="status" id="aging-status">Fetching latest data.</div>
        </div>

        <div class="panel search-panel" id="search-panel">
          <header>
            <div>
              <h3 class="panel-title">Inventory Search</h3>
              <div class="panel-sub">Search by style code or article name. Filter by department.</div>
            </div>
            <div class="search-block">
              <div class="search">
                <input class="search-input" id="search-input" placeholder="Search inventory" />
                <button class="button button-outline" id="search-button">Search</button>
              </div>
              <div class="filter-row">
                <div class="filter-label">Department</div>
                <div class="chip-row" id="department-filters">
                  <button class="chip toggle department-chip" type="button" data-department="Dress" aria-pressed="false">Dress</button>
                  <button class="chip toggle department-chip" type="button" data-department="Dress Material" aria-pressed="false">Dress Material</button>
                  <button class="chip toggle department-chip" type="button" data-department="Lehenga" aria-pressed="false">Lehenga</button>
                  <button class="chip toggle department-chip" type="button" data-department="Saree" aria-pressed="false">Saree</button>
                  <button class="chip clear" type="button" id="department-clear">Clear</button>
                </div>
              </div>
            </div>
          </header>

          <table>
            <thead>
              <tr>
                <th>Style</th>
                <th>Article</th>
                <th>Category</th>
                <th>Department</th>
                <th>Supplier</th>
                <th>Store</th>
                <th>Qty</th>
                <th>Days</th>
                <th>Item MRP</th>
                <th>Aging</th>
                <th>Danger</th>
              </tr>
            </thead>
            <tbody id="search-rows">
              <tr><td class="empty" colspan="11">Enter a query or select a department to search inventory.</td></tr>
            </tbody>
          </table>
          <div class="status" id="search-status">Waiting for query or department filter.</div>
        </div>
      </section>
      </main>
    </div>

    <div class="toast" id="toast" role="status" aria-live="polite"></div>

    <script>
      const formatCurrency = new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 0,
      });

      const formatDate = (value) => {
        if (!value) return "--";
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return value;
        return date.toLocaleDateString("en-IN", {
          year: "numeric",
          month: "short",
          day: "numeric",
        });
      };

      const toast = document.getElementById("toast");
      let toastTimer = null;
      const notify = (message, variant = "") => {
        if (!toast) return;
        toast.textContent = message;
        toast.className = `toast show ${variant}`.trim();
        if (toastTimer) {
          clearTimeout(toastTimer);
        }
        toastTimer = setTimeout(() => {
          toast.classList.remove("show");
        }, 2800);
      };

      let agingCache = [];
      let lastSearchResults = [];
      let automationCount = 0;
      let liveInterval = null;
      const liveIntervalMs = 60000;

      const renderEmpty = (message) => {
        const tbody = document.getElementById("store-rows");
        tbody.innerHTML = `<tr><td class="empty" colspan="5">${message}</td></tr>`;
      };

      const renderTable = (rows) => {
        const tbody = document.getElementById("store-rows");
        tbody.innerHTML = "";
        rows.forEach((row) => {
          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td class="store-id" data-label="Store">Store ${row.store_id}</td>
            <td data-label="Early"><span class="pill early">EARLY</span>${formatCurrency.format(row.EARLY || 0)}</td>
            <td data-label="High"><span class="pill high">HIGH</span>${formatCurrency.format(row.HIGH || 0)}</td>
            <td data-label="Critical"><span class="pill critical">CRITICAL</span>${formatCurrency.format(row.CRITICAL || 0)}</td>
            <td class="total" data-label="Total">${formatCurrency.format(row.total_danger_capital || 0)}</td>
          `;
          tbody.appendChild(tr);
        });
      };

      const renderAgingEmpty = (message) => {
        const tbody = document.getElementById("aging-rows");
        tbody.innerHTML = `<tr><td class="empty" colspan="6">${message}</td></tr>`;
      };

      const renderAgingTable = (rows) => {
        const tbody = document.getElementById("aging-rows");
        tbody.innerHTML = "";
        rows.forEach((row) => {
          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td class="store-id" data-label="Store">Store ${row.store_id}</td>
            <td data-label="Healthy"><span class="pill healthy">HEALTHY</span>${formatCurrency.format(row.HEALTHY || 0)}</td>
            <td data-label="Transfer"><span class="pill transfer">TRANSFER</span>${formatCurrency.format(row.TRANSFER || 0)}</td>
            <td data-label="RR_TT"><span class="pill rr-tt">RR_TT</span>${formatCurrency.format(row.RR_TT || 0)}</td>
            <td data-label="VERY_DANGER"><span class="pill very-danger">VERY_DANGER</span>${formatCurrency.format(row.VERY_DANGER || 0)}</td>
            <td class="total" data-label="Total">${formatCurrency.format(row.total_aging_capital || 0)}</td>
          `;
          tbody.appendChild(tr);
        });
      };

      const applyAgingFilter = () => {
        const input = document.getElementById("aging-search-input");
        const status = document.getElementById("aging-status");
        const query = input.value.trim().toLowerCase();

        if (!agingCache || agingCache.length === 0) {
          renderAgingEmpty("No inventory found.");
          status.textContent = "No inventory found.";
          return;
        }

        const filtered = query
          ? agingCache.filter((row) => String(row.store_id).toLowerCase().includes(query))
          : agingCache;

        if (filtered.length === 0) {
          renderAgingEmpty("No matches found.");
          status.textContent = "No matching stores.";
          return;
        }

        renderAgingTable(filtered);
        status.textContent = query
          ? `Showing ${filtered.length} stores for "${query}".`
          : "Latest aging summary loaded.";
      };

      const renderSearchEmpty = (message) => {
        const tbody = document.getElementById("search-rows");
        tbody.innerHTML = `<tr><td class="empty" colspan="11">${message}</td></tr>`;
      };

      const renderSearchTable = (rows) => {
        const tbody = document.getElementById("search-rows");
        tbody.innerHTML = "";
        rows.forEach((row) => {
          const level = row.danger_level || "NONE";
          const levelClass = level === "NONE" ? "none" : level.toLowerCase();
          const aging = row.aging_status || "UNKNOWN";
          const agingClass = aging === "UNKNOWN" ? "unknown" : aging.toLowerCase().replace(/_/g, "-");
          const categoryName = row.category_name || row.category || "--";
          const departmentName = row.department_name || "--";
          const supplierName = row.supplier_name ? row.supplier_name : "--";
          const ageDays = row.age_days == null ? "--" : row.age_days;
          let itemMrp = row.item_mrp;
          if (itemMrp == null) {
            itemMrp = row.mrp;
          }
          const itemMrpLabel = itemMrp == null ? "--" : formatCurrency.format(itemMrp);
          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td data-label="Style">${row.style_code}</td>
            <td data-label="Article">${row.article_name}</td>
            <td data-label="Category">${categoryName}</td>
            <td data-label="Department">${departmentName}</td>
            <td data-label="Supplier">${supplierName}</td>
            <td data-label="Store">Store ${row.store_id}</td>
            <td data-label="Qty">${row.quantity}</td>
            <td data-label="Days">${ageDays}</td>
            <td data-label="Item MRP">${itemMrpLabel}</td>
            <td data-label="Aging"><span class="pill ${agingClass}">${aging}</span></td>
            <td data-label="Danger"><span class="pill ${levelClass}">${level}</span></td>
          `;
          tbody.appendChild(tr);
        });
      };

      const departmentButtons = Array.from(document.querySelectorAll(".department-chip"));

      const getSelectedDepartments = () => (
        departmentButtons
          .filter((button) => button.classList.contains("active"))
          .map((button) => ({
            value: button.dataset.department,
            label: button.dataset.label || button.textContent.trim(),
          }))
      );

      const setDepartmentState = (button, isActive) => {
        button.classList.toggle("active", isActive);
        button.setAttribute("aria-pressed", isActive ? "true" : "false");
      };

      const clearDepartments = () => {
        departmentButtons.forEach((button) => setDepartmentState(button, false));
      };

      const updateSummary = (data) => {
        const total = data.results.reduce((acc, row) => acc + (row.total_danger_capital || 0), 0);
        document.getElementById("summary-total").textContent = formatCurrency.format(total);
        document.getElementById("summary-count").textContent = data.store_count;
        document.getElementById("as-of").textContent = `As of ${formatDate(data.date)}`;

        if (data.results.length > 0) {
          const top = [...data.results].sort((a, b) => b.total_danger_capital - a.total_danger_capital)[0];
          document.getElementById("summary-top").textContent = `Store ${top.store_id}`;
          document.getElementById("summary-top-note").textContent = `${formatCurrency.format(top.total_danger_capital)} at risk`;
        } else {
          document.getElementById("summary-top").textContent = "--";
          document.getElementById("summary-top-note").textContent = "No alert-visible inventory";
        }
      };

      const updateLatency = (latencyMs) => {
        if (!Number.isFinite(latencyMs)) {
          return;
        }
        const value = `${latencyMs} ms`;
        document.getElementById("summary-latency").textContent = value;
        document.getElementById("health-latency").textContent = value;
        const bar = document.getElementById("health-latency-bar");
        const normalized = Math.max(8, Math.min(100, 120 - latencyMs / 2));
        bar.style.width = `${normalized}%`;
      };

      const updateAutomation = () => {
        const label = `${automationCount} runs today`;
        const queued = `${automationCount} queued`;
        document.getElementById("automation-count").textContent = label;
        document.getElementById("health-automation").textContent = queued;
        const bar = document.getElementById("health-automation-bar");
        const width = Math.max(20, Math.min(100, 30 + automationCount * 12));
        bar.style.width = `${width}%`;
        document.getElementById("automation-latest").textContent = new Date().toLocaleTimeString("en-IN");
      };

      const csvEscape = (value) => {
        if (value == null) return "";
        const stringValue = String(value).replace(/"/g, '""');
        return `"${stringValue}"`;
      };

      const exportSearchResults = () => {
        if (!lastSearchResults || lastSearchResults.length === 0) {
          notify("No search results to export.", "success");
          return;
        }
        const headers = [
          "style_code",
          "article_name",
          "category",
          "department_name",
          "supplier_name",
          "store_id",
          "quantity",
          "age_days",
          "item_mrp",
          "aging_status",
          "danger_level",
        ];
        const lines = [headers.join(",")];
        lastSearchResults.forEach((row) => {
          const line = headers.map((key) => {
            const value = row[key] != null ? row[key] : row[key.replace("_name", "")];
            return csvEscape(value);
          }).join(",");
          lines.push(line);
        });
        const blob = new Blob([lines.join("\\n")], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `inventory_export_${new Date().toISOString().slice(0, 10)}.csv`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        notify(`Exported ${lastSearchResults.length} rows.`, "success");
      };

      const highlightFilters = () => {
        const panel = document.getElementById("search-panel");
        panel.classList.add("filters-open");
        panel.scrollIntoView({ behavior: "smooth", block: "center" });
        document.getElementById("search-input").focus();
        setTimeout(() => panel.classList.remove("filters-open"), 1400);
      };

      const flashAction = (button) => {
        button.classList.add("clicked");
        setTimeout(() => button.classList.remove("clicked"), 600);
      };

      const shouldRefreshSearch = () => {
        const query = document.getElementById("search-input").value.trim();
        const selectedDepartments = getSelectedDepartments();
        const hasQuery = query.length >= 2;
        const hasDepartmentOnly = query.length === 0 && selectedDepartments.length > 0;
        return hasQuery || hasDepartmentOnly;
      };

      const refreshAll = () => {
        loadDashboard();
        if (shouldRefreshSearch()) {
          searchInventory();
        }
      };

      const setLiveMode = (enabled) => {
        const liveToggle = document.getElementById("live-toggle");
        liveToggle.classList.toggle("off", !enabled);
        liveToggle.setAttribute("aria-pressed", enabled ? "true" : "false");
        if (liveInterval) {
          clearInterval(liveInterval);
        }
        if (enabled) {
          liveInterval = setInterval(refreshAll, liveIntervalMs);
        }
      };

      const actionHandlers = {
        refresh: () => {
          refreshAll();
          notify("Live data refreshed.", "success");
        },
        export: exportSearchResults,
        filters: () => {
          highlightFilters();
          notify("Filters ready for selection.", "success");
        },
        automate: () => {
          automationCount += 1;
          updateAutomation();
          notify("Automation workflow queued.", "success");
        },
      };

      const loadDashboard = async () => {
        const status = document.getElementById("status");
        const agingStatus = document.getElementById("aging-status");
        status.textContent = "Refreshing data...";
        agingStatus.textContent = "Refreshing data...";
        const start = performance.now();
        try {
          const response = await fetch("store-danger-summary");
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
          }
          const data = await response.json();
          updateLatency(Math.round(performance.now() - start));
          if (!data.results || data.results.length === 0) {
            renderEmpty("No alert-visible inventory found.");
          } else {
            const sorted = [...data.results].sort(
              (a, b) => b.total_danger_capital - a.total_danger_capital
            );
            renderTable(sorted);
          }

          agingCache = [...(data.aging_results || [])].sort(
            (a, b) => b.total_aging_capital - a.total_aging_capital
          );
          applyAgingFilter();
          updateSummary(data);
          status.textContent = "Latest data loaded.";
        } catch (error) {
          renderEmpty("Unable to load data. Check the API and try again.");
          status.textContent = `Error: ${error.message}`;
          renderAgingEmpty("Unable to load data. Check the API and try again.");
          agingStatus.textContent = `Error: ${error.message}`;
        }
      };

      const searchInventory = async () => {
        const input = document.getElementById("search-input");
        const status = document.getElementById("search-status");
        const query = input.value.trim();
        const selectedDepartments = getSelectedDepartments();
        const departmentValues = selectedDepartments.map((item) => item.value);

        if (query.length > 0 && query.length < 2) {
          renderSearchEmpty("Enter at least 2 characters or clear the query.");
          status.textContent = "Waiting for query or department filter.";
          lastSearchResults = [];
          return;
        }

        if (query.length === 0 && departmentValues.length === 0) {
          renderSearchEmpty("Enter at least 2 characters or select a department.");
          status.textContent = "Waiting for query or department filter.";
          lastSearchResults = [];
          return;
        }

        status.textContent = "Searching...";
        try {
          const params = new URLSearchParams();
          if (query.length >= 2) {
            params.set("query", query);
          }
          if (departmentValues.length > 0) {
            params.set("department", departmentValues.join(","));
          }

          const response = await fetch(`/search/inventory?${params.toString()}`);
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
          }
          const data = await response.json();
          lastSearchResults = data.results || [];
          if (!data.results || data.results.length === 0) {
            renderSearchEmpty("No matches found.");
          } else {
            renderSearchTable(data.results);
          }
          const queryLabel = query.length >= 2 ? ` for "${query}"` : "";
          const departmentLabel = selectedDepartments.length
            ? ` in ${selectedDepartments.map((item) => item.label).join(", ")}`
            : "";
          status.textContent = `Found ${data.count} items${queryLabel}${departmentLabel}.`;
        } catch (error) {
          renderSearchEmpty("Search failed. Check the API and try again.");
          status.textContent = `Error: ${error.message}`;
          lastSearchResults = [];
        }
      };

      document.getElementById("aging-search-button").addEventListener("click", applyAgingFilter);
      document.getElementById("search-button").addEventListener("click", searchInventory);
      departmentButtons.forEach((button) => {
        button.addEventListener("click", () => {
          setDepartmentState(button, !button.classList.contains("active"));
        });
      });
      document.getElementById("department-clear").addEventListener("click", () => {
        clearDepartments();
      });
      document.getElementById("aging-search-input").addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          applyAgingFilter();
        }
      });
      document.getElementById("search-input").addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          searchInventory();
        }
      });

      document.getElementById("live-toggle").addEventListener("click", () => {
        const enabled = document.getElementById("live-toggle").getAttribute("aria-pressed") !== "true";
        setLiveMode(enabled);
        notify(enabled ? "Live sync enabled." : "Live sync paused.");
      });

      document.querySelectorAll(".action-pill").forEach((button) => {
        button.addEventListener("click", () => {
          flashAction(button);
          button.classList.toggle("active");
          const action = button.dataset.action;
          const handler = actionHandlers[action];
          if (handler) {
            handler();
          }
        });
      });

      setLiveMode(true);
      loadDashboard();
    </script>
  </body>
</html>
"""


@router.get("/", response_class=HTMLResponse)
def dashboard_page():
    return HTMLResponse(_DASHBOARD_HTML)


@router.get("/store-danger-summary")
def store_wise_danger_summary():
    """
    Store-wise capital summary for ALERT-VISIBLE inventory only
    (EARLY / HIGH / CRITICAL), plus aging status across all inventory.
    """

    # noinspection SqlNoDataSourceInspection
    sql = text("""
        SELECT
            i.store_id,
            i.quantity,
            i.cost_price,
            i.lifecycle_start_date,
            p.category
        FROM inventory i
        LEFT JOIN products p ON p.id = i.product_id
    """)

    today = date.today()
    danger_summary = {}
    aging_summary = {}

    with engine.connect() as conn:
        rows = conn.execute(sql).mappings().all()

    for row in rows:
        store_id = row["store_id"]
        capital = row["quantity"] * row["cost_price"]
        level = danger_level(row["lifecycle_start_date"])

        # =========================
        # ONLY ALERT-VISIBLE ITEMS
        # =========================
        if level is not None:
            if store_id not in danger_summary:
                danger_summary[store_id] = {
                    "store_id": store_id,
                    "EARLY": 0.0,
                    "HIGH": 0.0,
                    "CRITICAL": 0.0,
                    "total_danger_capital": 0.0,
                }

            danger_summary[store_id][level] += capital
            danger_summary[store_id]["total_danger_capital"] += capital

        age_days = calculate_age_in_days(row["lifecycle_start_date"])
        if age_days is None:
            continue

        # Aging status uses category rules with default thresholds for unknown categories.
        aging_status = classify_status_with_default(row["category"], age_days)

        if store_id not in aging_summary:
            aging_summary[store_id] = {
                "store_id": store_id,
                "HEALTHY": 0.0,
                "TRANSFER": 0.0,
                "RR_TT": 0.0,
                "VERY_DANGER": 0.0,
                "total_aging_capital": 0.0,
            }

        aging_summary[store_id][aging_status] += capital
        aging_summary[store_id]["total_aging_capital"] += capital

    return {
        "date": today,
        "store_count": len(danger_summary),
        "results": list(danger_summary.values()),
        "aging_results": list(aging_summary.values()),
    }
