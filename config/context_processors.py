from .version import VERSION


def version_context(request):
    return {"version": VERSION}
