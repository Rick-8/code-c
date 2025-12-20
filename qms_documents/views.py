from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.db.models import Q
from .models import ControlledDocument, DocumentVersion
from .forms import PasswordConfirmForm, DocumentEditForm, ControlledDocumentCreateForm
from django.template.loader import render_to_string
from django.http import JsonResponse


def _user_can_edit(user):
    return user.is_authenticated and user.is_staff


def document_list(request):
    q = request.GET.get("q", "").strip()

    documents = ControlledDocument.objects.all().order_by("category", "reference")

    if q:
        documents = documents.filter(
            Q(reference__icontains=q) |
            Q(title__icontains=q) |
            Q(category__icontains=q)
        )

    # If it's an AJAX call, just return the table rows as HTML
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        html = ""
        if documents.exists():
            for doc in documents:
                html += f"""
                <tr>
                    <td><strong>{doc.reference}</strong></td>
                    <td>{doc.title}</td>
                    <td>{doc.category}</td>
                    <td><span class='badge {"qms-badge-approved" if doc.status=="APPROVED" else "qms-badge-draft" if doc.status=="DRAFT" else "qms-badge-obsolete"}'>
                        {doc.get_status_display()}</span></td>
                    <td class='text-end'>
                        <a href='/qms-documents/{doc.reference}/' class='btn btn-sm btn-qms-open'>Open</a>
                    </td>
                </tr>
                """
        else:
            html = """
            <tr>
                <td colspan='5' class='text-center qms-muted py-4'>No documents found.</td>
            </tr>
            """
        return JsonResponse({"html": html})

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

    # Check permissions
    if not _user_can_edit(request.user):
        messages.error(request, "You do not have permission to edit documents.")
        return redirect("document_detail", reference=reference)

    # Must have passed password confirmation
    if not request.session.get(f"doc_edit_ok_{document.pk}"):
        return redirect("confirm_edit", reference=reference)

    # Get the current version if one exists
    current = document.current_version
    initial_content = current.content if current else ""

    if request.method == "POST":
        form = DocumentEditForm(request.POST)
        if form.is_valid():
            change_summary = form.cleaned_data["change_summary"]
            content = form.cleaned_data["content"]

            # --- Superuser-only: allow status update ---
            if request.user.is_superuser and "status" in request.POST:
                new_status = request.POST.get("status")
                if new_status and new_status != document.status:
                    document.status = new_status
                    document.save(update_fields=["status"])
                    messages.info(
                        request,
                        f"Document status updated to {document.get_status_display()}."
                    )

            # --- Create new version ---
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

            # Clear edit session flag
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


@login_required
def document_change_status(request, reference):
    document = get_object_or_404(ControlledDocument, reference=reference)

    if not _user_can_edit(request.user):
        messages.error(request, "You do not have permission to change document status.")
        return redirect("document_detail", reference=reference)

    if request.method == "POST":
        form = DocumentStatusForm(request.POST, instance=document)
        if form.is_valid():
            form.save()
            messages.success(request, f"Status updated to {document.get_status_display()}.")
            return redirect("document_detail", reference=reference)
    else:
        form = DocumentStatusForm(instance=document)

    return render(request, "qms_documents/document_change_status.html", {
        "document": document,
        "form": form,
    })
