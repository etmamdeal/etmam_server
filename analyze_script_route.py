
from flask import request, render_template, redirect, url_for, flash
import ast
import os

@bp.route('/analyze-script', methods=['POST'])
def analyze_script():
    uploaded_file = request.files.get('script_file')
    if not uploaded_file or not uploaded_file.filename.endswith('.py'):
        flash("الرجاء رفع ملف Python صالح.", "danger")
        return redirect(url_for('main.smart_script_upload'))

    # حفظ الملف مؤقتاً
    upload_path = os.path.join('uploads', uploaded_file.filename)
    os.makedirs('uploads', exist_ok=True)
    uploaded_file.save(upload_path)

    # تحليل الملف لاستخلاص المتغيرات والدوال
    try:
        with open(upload_path, 'r', encoding='utf-8') as f:
            source = f.read()

        parsed = ast.parse(source)

        functions = []
        for node in parsed.body:
            if isinstance(node, ast.FunctionDef):
                args = [arg.arg for arg in node.args.args]
                functions.append({
                    'name': node.name,
                    'parameters': args
                })

        result = {
            'filename': uploaded_file.filename,
            'functions': functions,
        }

        return render_template('script_analysis_result.html', result=result)

    except Exception as e:
        flash(f"حدث خطأ أثناء تحليل السكربت: {str(e)}", "danger")
        return redirect(url_for('main.smart_script_upload'))
