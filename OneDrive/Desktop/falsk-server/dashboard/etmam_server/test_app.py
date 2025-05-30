from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return '<h1>تطبيق الاختبار يعمل!</h1><p>إذا رأيت هذه الرسالة، فإن Flask يعمل بشكل صحيح.</p>'

@app.route('/test')
def test():
    return 'صفحة الاختبار تعمل على المنفذ 8080'

if __name__ == '__main__':
    print("🚀 بدء تشغيل تطبيق الاختبار على http://127.0.0.1:8080")
    app.run(debug=True, host='0.0.0.0', port=8080) 