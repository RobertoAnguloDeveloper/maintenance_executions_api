import csv
import io
import xlsxwriter
from flask import send_file
from app.models import Form, FormSubmission, Question, Answer
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

class ExportService:
    @staticmethod
    def export_form_data(form_id, format='csv'):
        form = Form.query.get(form_id)
        if not form:
            raise ValueError("Form not found")

        submissions = FormSubmission.query.filter_by(form_id=form_id).all()
        questions = Question.query.filter_by(form_id=form_id).order_by(Question.order_number).all()

        if format == 'csv':
            return ExportService._export_csv(form, submissions, questions)
        elif format == 'excel':
            return ExportService._export_excel(form, submissions, questions)
        elif format == 'pdf':
            return ExportService._export_pdf(form, submissions, questions)
        else:
            raise ValueError("Unsupported export format")

    @staticmethod
    def _export_csv(form, submissions, questions):
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        header = ['Submission ID'] + [q.text for q in questions]
        writer.writerow(header)

        # Write data
        for submission in submissions:
            row = [submission.id]
            for question in questions:
                answer = Answer.query.filter_by(form_submission_id=submission.id, question_id=question.id).first()
                row.append(answer.value if answer else '')
            writer.writerow(row)

        output.seek(0)
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            attachment_filename=f'{form.title}_export.csv'
        )

    @staticmethod
    def _export_excel(form, submissions, questions):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet()

        # Write header
        header = ['Submission ID'] + [q.text for q in questions]
        for col, value in enumerate(header):
            worksheet.write(0, col, value)

        # Write data
        for row, submission in enumerate(submissions, start=1):
            worksheet.write(row, 0, submission.id)
            for col, question in enumerate(questions, start=1):
                answer = Answer.query.filter_by(form_submission_id=submission.id, question_id=question.id).first()
                worksheet.write(row, col, answer.value if answer else '')

        workbook.close()
        output.seek(0)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            attachment_filename=f'{form.title}_export.xlsx'
        )

    @staticmethod
    def _export_pdf(form, submissions, questions):
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        # Write title
        p.setFont("Helvetica-Bold", 16)
        p.drawString(50, height - 50, form.title)

        # Write data
        p.setFont("Helvetica", 10)
        y = height - 80
        for submission in submissions:
            if y < 50:  # New page if not enough space
                p.showPage()
                y = height - 50
            p.drawString(50, y, f"Submission ID: {submission.id}")
            y -= 20
            for question in questions:
                if y < 50:  # New page if not enough space
                    p.showPage()
                    y = height - 50
                answer = Answer.query.filter_by(form_submission_id=submission.id, question_id=question.id).first()
                p.drawString(70, y, f"{question.text}: {answer.value if answer else ''}")
                y -= 15
            y -= 10

        p.showPage()
        p.save()

        buffer.seek(0)
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            attachment_filename=f'{form.title}_export.pdf'
        )