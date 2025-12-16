from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import ControlledDocument, DocumentVersion
from .forms import PasswordConfirmForm, DocumentEditForm, ControlledDocumentCreateForm


def _user_can_edit(user):
    return user.is_authenticated and user.is_staff


def document_list(request):
    documents = ControlledDocument.objects.all().order_by("category", "reference")
    return render(request, "qms_documents/document_list.html", {
        "documents": documents,
    })


def document_detail(request, reference):
    document = get_object_or_404(ControlledDocument, reference=reference)
    current_version = document.current_version
    versions = document.versions.all()

    return render(request, "qms_documents/document_detail.html", {
        "document": document,
        "current_version": current_version,
        "versions": versions,
        "can_edit": _user_can_edit(request.user),
    })


def document_version_detail(request, reference, major, minor):
    document = get_object_or_404(ControlledDocument, reference=reference)

    version = document.versions.filter(
        version_major=major,
        version_minor=minor
    ).first()

    if not version:
        raise Http404("Document version not found")

    return render(request, "qms_documents/document_version_detail.html", {
        "document": document,
        "version": version,
    })


@login_required
def confirm_edit(request, reference):
    document = get_object_or_404(ControlledDocument, reference=reference)

    if not _user_can_edit(request.user):
        messages.error(request, "You do not have permission to edit documents.")
        return redirect("document_detail", reference=reference)

    if request.method == "POST":
        form = PasswordConfirmForm(request.POST)
        if form.is_valid():
            password = form.cleaned_data["password"]
            user = authenticate(
                request,
                username=request.user.get_username(),
                password=password,
            )
            if user:
                request.session[f"doc_edit_ok_{document.pk}"] = timezone.now().isoformat()
                return redirect("document_edit", reference=reference)
            messages.error(request, "Incorrect password.")
    else:
        form = PasswordConfirmForm()

    return render(request, "qms_documents/confirm_edit.html", {
        "document": document,
        "form": form,
    })


@login_required
def document_edit(request, reference):
    document = get_object_or_404(ControlledDocument, reference=reference)

    if not _user_can_edit(request.user):
        messages.error(request, "You do not have permission to edit documents.")
        return redirect("document_detail", reference=reference)

    if not request.session.get(f"doc_edit_ok_{document.pk}"):
        return redirect("confirm_edit", reference=reference)

    current = document.current_version
    initial_content = current.content if current else ""

    if request.method == "POST":
        form = DocumentEditForm(request.POST)
        if form.is_valid():
            change_summary = form.cleaned_data["change_summary"]
            content = form.cleaned_data["content"]

            if current:
                current.is_current = False
                current.save(update_fields=["is_current"])
                major = current.version_major
                minor = current.version_minor + 1
            else:
                major, minor = 1, 0

            DocumentVersion.objects.create(
                document=document,
                version_major=major,
                version_minor=minor,
                content=content,
                change_summary=change_summary,
                created_by=request.user,
                is_current=True,
            )

            request.session.pop(f"doc_edit_ok_{document.pk}", None)

            messages.success(request, f"Saved new version v{major}.{minor}")
            return redirect("document_detail", reference=reference)
    else:
        form = DocumentEditForm(initial={"content": initial_content})

    return render(request, "qms_documents/document_edit.html", {
        "document": document,
        "form": form,
        "current": current,
    })


@login_required
def document_create(request):
    if not _user_can_edit(request.user):
        messages.error(request, "You do not have permission to create documents.")
        return redirect("document_list")

    if request.method == "POST":
        form = ControlledDocumentCreateForm(request.POST)
        if form.is_valid():
            document = form.save(commit=False)
            document.owner = request.user
            document.save()

            messages.success(
                request,
                f"Document {document.reference} created. Add the first version."
            )
            return redirect("document_edit", reference=document.reference)
    else:
        form = ControlledDocumentCreateForm()

    return render(request, "qms_documents/document_create.html", {
        "form": form,
    })
