from app import db
from app.models import (
    QuestionType, Question, Answer, Form, FormQuestion, 
    FormAnswer, FormSubmission, AnswerSubmitted, Attachment
)
from datetime import datetime, timedelta
import logging
from app.models.user import User
import random

logger = logging.getLogger(__name__)

class TestDataCreator:
    def __init__(self, app):
        self.app = app

    def create_question_types(self):
        """Create basic question types"""
        types = [
            ('single_text', 'Texto libre, una respuesta'),
            ('multiple_choice', 'Selección múltiple'),
            ('single_choice', 'Selección única'),
            ('date', 'Fecha')
        ]
        
        created_types = []
        for type_name, description in types:
            qt = QuestionType.query.filter_by(type=type_name).first()
            if not qt:
                qt = QuestionType(type=type_name)
                db.session.add(qt)
                logger.info(f"Created question type: {type_name}")
            created_types.append(qt)
        
        db.session.commit()
        return created_types

    def create_project_questions(self):
        """Create project evaluation questions"""
        questions_data = [
            {
                'text': '¿Cuál es el nombre del proyecto?',
                'type': 'single_text',
                'order': 1,
                'has_remarks': False
            },
            {
                'text': 'Seleccione las áreas involucradas',
                'type': 'multiple_choice',
                'order': 2,
                'has_remarks': True
            },
            {
                'text': '¿Cuál es el estado actual del proyecto?',
                'type': 'single_choice',
                'order': 3,
                'has_remarks': True
            },
            {
                'text': 'Fecha estimada de finalización',
                'type': 'date',
                'order': 4,
                'has_remarks': False
            },
            {
                'text': 'Seleccione los riesgos identificados',
                'type': 'multiple_choice',
                'order': 5,
                'has_remarks': True
            }
        ]

        created_questions = []
        for q_data in questions_data:
            q_type = QuestionType.query.filter_by(type=q_data['type']).first()
            if not q_type:
                continue

            question = Question(
                text=q_data['text'],
                question_type_id=q_type.id,
                order_number=q_data['order'],
                has_remarks=q_data['has_remarks']
            )
            db.session.add(question)
            created_questions.append(question)

        db.session.commit()
        return created_questions

    def create_project_answers(self):
        """Create project evaluation answers"""
        answers_data = [
            # Respuesta para nombre del proyecto
            'Modernización Sistema Core',
            
            # Respuestas para áreas involucradas
            'Desarrollo',
            'QA',
            'Infraestructura',
            
            # Respuestas para estado del proyecto
            'En progreso',
            'Completado',
            'Retrasado',
            'En pausa',
            
            # Respuesta para fecha
            '2024-12-31',
            
            # Respuestas para riesgos
            'Retraso en entregas',
            'Problemas de integración',
            'Falta de recursos',
            'Cambios de alcance',
            'Problemas técnicos',
            'Dependencias externas'
        ]

        created_answers = []
        for value in answers_data:
            answer = Answer.query.filter_by(value=value).first()
            if not answer:
                answer = Answer(value=value)
                db.session.add(answer)
                logger.info(f"Created answer option: {value}")
            created_answers.append(answer)

        db.session.commit()
        return created_answers

    def create_project_forms(self):
        """Create project evaluation forms"""
        admin_user = User.query.filter_by(username='datacentermanager').first()
        if not admin_user:
            logger.error("Admin user not found")
            return []

        forms_data = [
            {
                'title': 'Evaluación de Proyecto 2024',
                'description': 'Formulario para evaluación trimestral de proyectos',
                'is_public': True
            },
            {
                'title': 'Evaluación de Riesgos de Proyecto',
                'description': 'Formulario para evaluación de riesgos y mitigaciones',
                'is_public': True
            },
            {
                'title': 'Reporte de Avance de Proyecto',
                'description': 'Formulario para reportar el avance mensual del proyecto',
                'is_public': True
            }
        ]

        created_forms = []
        questions = Question.query.all()
        
        for form_data in forms_data:
            form = Form.query.filter_by(title=form_data['title']).first()
            if not form:
                form = Form(
                    title=form_data['title'],
                    description=form_data['description'],
                    user_id=admin_user.id,
                    is_public=form_data['is_public']
                )
                db.session.add(form)
                db.session.flush()

                # Add questions to form
                for i, question in enumerate(questions, 1):
                    form_question = FormQuestion(
                        form_id=form.id,
                        question_id=question.id,
                        order_number=i
                    )
                    db.session.add(form_question)

                created_forms.append(form)
                logger.info(f"Created form: {form_data['title']}")

        db.session.commit()
        return created_forms

    def create_sample_submissions(self):
        """Create sample form submissions"""
        try:
            # Get first form and its questions
            form = Form.query.first()
            if not form:
                logger.error("No forms found")
                return False

            form_questions = FormQuestion.query.filter_by(form_id=form.id).all()
            answers = Answer.query.all()

            # Create a submission
            submission = FormSubmission(
                form_id=form.id,
                submitted_by='datacentermanager',
                submitted_at=datetime.utcnow()
            )
            db.session.add(submission)
            db.session.flush()

            # Create form answers and link them to submission
            for fq in form_questions:
                # Select appropriate answer based on question type
                question = Question.query.get(fq.question_id)
                suitable_answers = [a for a in answers if len(a.value) > 0]  # Filter out empty answers
                answer = random.choice(suitable_answers)

                form_answer = FormAnswer(
                    form_question_id=fq.id,
                    answer_id=answer.id,
                    remarks='Observación de ejemplo' if question.has_remarks else None
                )
                db.session.add(form_answer)
                db.session.flush()

                # Link answer to submission
                answer_submitted = AnswerSubmitted(
                    form_answer_id=form_answer.id,
                    form_submission_id=submission.id
                )
                db.session.add(answer_submitted)

            # Add sample attachments
            attachments_data = [
                {
                    'file_type': 'pdf',
                    'file_path': '/storage/projects/cronograma.pdf',
                    'is_signature': False
                },
                {
                    'file_type': 'xlsx',
                    'file_path': '/storage/projects/riesgos.xlsx',
                    'is_signature': False
                },
                {
                    'file_type': 'png',
                    'file_path': '/storage/projects/firma_aprobacion.png',
                    'is_signature': True
                }
            ]

            for att_data in attachments_data:
                attachment = Attachment(
                    form_submission_id=submission.id,
                    **att_data
                )
                db.session.add(attachment)

            db.session.commit()
            return True

        except Exception as e:
            logger.error(f"Error creating sample submissions: {str(e)}")
            db.session.rollback()
            return False

    def create_test_data(self):
        """Create all test data"""
        try:
            print("\n🚀 Creating project evaluation test data...")
            
            print("\n1️⃣  Creating question types...")
            self.create_question_types()
            print("✅ Question types created successfully")
            
            print("\n2️⃣  Creating project questions...")
            self.create_project_questions()
            print("✅ Questions created successfully")
            
            print("\n3️⃣  Creating answer options...")
            self.create_project_answers()
            print("✅ Answer options created successfully")
            
            print("\n4️⃣  Creating evaluation forms...")
            self.create_project_forms()
            print("✅ Forms created successfully")

            print("\n5️⃣  Creating sample submissions...")
            if self.create_sample_submissions():
                print("✅ Sample submissions created successfully")
            else:
                print("❌ Error creating sample submissions")
            
            print("\n✅ Test data creation completed successfully!")
            return True, None
            
        except Exception as e:
            db.session.rollback()
            error_msg = f"Error creating test data: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

def create_test_data():
    print("\n🔧 Project Evaluation Test Data Creation")
    print("=====================================")
    
    try:
        from app import create_app
        app = create_app()
        with app.app_context():
            creator = TestDataCreator(app)
            success, error = creator.create_test_data()
            
            if success:
                print("\n🎉 Success! Test data has been created successfully.")
            else:
                print(f"\n❌ Error: {error}")
                print("Please check the logs for more details.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        print("Please check the logs for more details.")

if __name__ == "__main__":
    create_test_data()