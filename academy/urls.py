from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="academy_dashboard"),
    path("course/<slug:course_slug>/", views.course_detail, name="academy_course_detail"),
    path("course/<slug:course_slug>/module/<slug:module_slug>/", views.module_detail, name="academy_module_detail"),
    path("course/<slug:course_slug>/module/<slug:module_slug>/lesson/<int:lesson_id>/", views.lesson_detail, name="academy_lesson_detail"),
    path("lesson/<int:lesson_id>/complete/", views.academy_complete_lesson, name="academy_complete_lesson"),
    path("course/<slug:course_slug>/module/<slug:module_slug>/quiz/", views.module_quiz, name="academy_module_quiz"),
    path("course/<slug:course_slug>/module/<slug:module_slug>/final-test/", views.final_test, name="academy_final_test"),
    path("certificate/<int:certificate_id>/", views.certificate_detail, name="academy_certificate_detail"),
    path("managers/", views.manager_dashboard, name="academy_manager_dashboard"),
    path("managers/final-tests/", views.manager_final_tests, name="academy_manager_final_tests"),
    path("managers/driver-progress/", views.manager_driver_progress, name="academy_manager_driver_progress"),
    path("managers/documents/", views.manager_documents, name="academy_manager_documents"),
    path("managers/tools/", views.manager_tools, name="academy_manager_tools"),
    path("managers/certificates/", views.manager_certificates, name="academy_manager_certificates"),
    path("managers/certificate/<int:certificate_id>/pdf/", views.generate_certificate_pdf, name="academy_generate_certificate_pdf"),
    path(
        "managers/final-tests/pass/<int:submission_id>/",
        views.manager_mark_pass,
        name="academy_manager_mark_pass"
    ),
    path("managers/users/", views.manager_users, name="academy_manager_users"),
    path("questions/add/", views.add_question, name="academy_add_question"),


]
