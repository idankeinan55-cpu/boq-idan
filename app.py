"""
מחולל כתב כמויות — אידן
Flask + Google Gemini (חינם)
"""

from flask import Flask, request, jsonify, session, send_from_directory
import google.generativeai as genai
import base64, json, re, os
from PIL import Image
import io

app = Flask(__name__, static_folder='public', static_url_path='')
app.secret_key = os.environ.get('SECRET_KEY', 'boq-idan-2026-secret')

# ==========================================
# הגדרות — שנה כאן
# ==========================================
APP_PASSWORD   = os.environ.get('APP_PASSWORD', 'idan2026')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

# ==========================================
# SYSTEM PROMPT — כל הידע
# ==========================================
SYSTEM_PROMPT = """אתה מומחה לכתיבת כתבי כמויות (כב"כ) לפרויקטי בנייה ושיפוץ בישראל.
נתח את התוכניות שמועלות ותפיק כתב כמויות מפורט ומדויק.

## כללי ברזל:
- פרק 06 = נגרות אומן
- פרק 07 = מתקני תברואה
- פרק 08 = מערכות חשמל ותקשורת
- פרק 10 = ריצוף וחיפוי
- פרק 11 = צביעה
- פרק 12 = מחיצות מודולריות
- פרק 15 = מיזוג (תמיד קומפ' אחד בלבד!)
- פרק 22 = גבס + תקרות
- פרק 34 = גילוי אש + ספרינקלרים
- פרק 69 = ברג'י ושונות

## חוקים:
- מיזוג = חוזה נפרד, רשום קומפ' ללא מחיר פירוט
- שיש = אורך × 2 (כולל חיפוי אחורי)
- ארון גדול במשרד = ארון טכני/מדפסת, לא תלבושות!
- מחיצה גבס+זכוכית: מדוד נפרד

## מחירון ישראל 2026:

נגרות משרד:
- ארון מדפסת/חשמל/תקשורת: 16,800 קומפ'
- מטבח משרדי עליון+תחתון+בר: 17,600 קומפ'
- ארון אחסון 207/40: 8,760 קומפ'
- דלת פורמייקה: 1,200

נגרות דירה:
- ארון תלבושות עד 300 ס"מ: 15,000
- מטבח ביתי: 4,500/מ"ר
- ספרייה/ארון קיר: 3,500/מ"ר

תברואה:
- נק' אינסטלציה לכיור: 2,125/נק'
- מתקן שאיבה סילוקית: 5,500
- כיור נרוסטה 55: 1,980
- ברז מטבח נשלף: 1,690
- אסלה תלויה: 1,900
- מיכל הדחה TECE: 810
- ניקוז מזגן PVC: 1,000/נק'

חשמל:
- נק' מחשב CAT7: 387/נק'
- קופסת עדה 18D: 662/נק'
- שקע כפול: 300/נק'
- שקע מיזוג: 500
- פנל LED 60x60: 662/נק'
- לוח חשמל 3x40A: 6,625

ריצוף:
- מילוא מתפלס: 180/מ"ר
- SPC אספקה+התקנה: 245/מ"ר
- גרניט 60x60: 370/מ"ר
- גרניט 120x120: 420/מ"ר
- שיש קוורץ: 2,000/מטר

צביעה:
- קירות: 65/מ"ר
- תקרות: 65/מ"ר
- ווש: 100/מ"ר

גבס:
- מחיצה 10 ס"מ: 243/מ"ר
- חיפוי גבס: 156/מ"ר
- גבס ירוק: 262/מ"ר
- תקרת גבס: 250/מ"ר
- תקרת אקוסטיקה 60x60: 300/מ"ר
- BAFFLE BEAM 210 ס"מ: 725/יח'

מחיצות מודולריות:
- זכוכית ר"ת: 875/מ"ר
- דלת זכוכית: 4,062
- דלת אטומה שירותים: 5,250

ברג'י:
- ניקיון כללי: 9,000
- מכולה 12 מ"ק: 2,500/יח'
- אישור בטיחות: 4,000

## פורמט תשובה — JSON בלבד, ללא טקסט אחר:
{
  "project_type": "סוג הפרויקט",
  "project_summary": "תיאור קצר",
  "chapters": [
    {
      "chapter_num": "06",
      "chapter_name": "נגרות אומן",
      "items": [
        {
          "id": "06.1.010",
          "description": "תיאור מפורט",
          "unit": "קומפ'",
          "quantity": 1,
          "unit_price": 16800,
          "total": 16800,
          "notes": ""
        }
      ],
      "chapter_total": 16800
    }
  ],
  "grand_total": 16800,
  "notes": ["הערות חשובות"]
}"""


# ==========================================
# ROUTES
# ==========================================

@app.route('/')
def index():
    return send_from_directory('public', 'index.html')


@app.route('/api/login', methods=['POST'])
def login():
    data = request.json or {}
    if data.get('password') == APP_PASSWORD:
        session['logged_in'] = True
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'סיסמה שגויה'}), 401


@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})


@app.route('/api/analyze', methods=['POST'])
def analyze():
    if not session.get('logged_in'):
        return jsonify({'error': 'לא מחובר'}), 401

    gemini_key = GEMINI_API_KEY or request.headers.get('x-gemini-key', '')
    if not gemini_key:
        return jsonify({'error': 'חסר Gemini API Key'}), 400

    project_type = request.form.get('projectType', 'משרדים')
    notes_text   = request.form.get('notes', '')
    files        = request.files.getlist('plans')

    if not files:
        return jsonify({'error': 'לא הועלו קבצים'}), 400

    try:
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel('gemini-1.5-flash')

        # בנה תוכן
        parts = [SYSTEM_PROMPT]

        for f in files:
            img_bytes = f.read()
            try:
                img = Image.open(io.BytesIO(img_bytes))
                # המר ל-RGB אם צריך
                if img.mode not in ('RGB', 'L'):
                    img = img.convert('RGB')
                buf = io.BytesIO()
                img.save(buf, format='JPEG', quality=90)
                parts.append({
                    'mime_type': 'image/jpeg',
                    'data': buf.getvalue()
                })
            except Exception:
                # אם לא תמונה — נסה כ-bytes ישיר
                parts.append({
                    'mime_type': f.content_type or 'image/jpeg',
                    'data': img_bytes
                })

        user_msg = f"\nסוג פרויקט: {project_type}\n"
        if notes_text:
            user_msg += f"הערות: {notes_text}\n"
        user_msg += "\nנתח את התוכניות ותחזיר JSON בלבד."
        parts.append(user_msg)

        response = model.generate_content(parts)
        raw = response.text

        # חלץ JSON
        json_match = re.search(r'\{[\s\S]*\}', raw)
        boq = json.loads(json_match.group() if json_match else raw)

        return jsonify({'success': True, 'boq': boq})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    print(f"\n[OK] Server running on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
