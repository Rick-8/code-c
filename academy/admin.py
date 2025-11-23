from django.contrib import admin
from .models import ManagerDocument
from .models import (
    Course,
    Module,
    Lesson,
    Question,
    Choice,
    ModuleProgress,
    LessonProgress,
    FinalTestSubmission,
)

admin.site.register(Course)
admin.site.register(Module)
admin.site.register(Lesson)
admin.site.register(Question)
admin.site.register(Choice)
admin.site.register(ModuleProgress)
admin.site.register(LessonProgress)
admin.site.register(FinalTestSubmission)
admin.site.register(ManagerDocument)
