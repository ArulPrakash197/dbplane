from django.shortcuts import render
import secrets
import string


def generate_secure_code(mode):
    """
    Helper function to generate cryptographically secure strings.
    Using 'secrets' is safer than 'random' for security purposes.
    """
    if mode == 'pin':
        # Generate a 4-digit PIN
        return ''.join(secrets.choice(string.digits) for _ in range(4))

    # Password logic: Use a 'Clean' set to avoid confusing characters
    # (Removed: i, l, 1, L, o, O, 0)
    lowercase = "abcdefghjkmnpqrstuvwxyz"
    uppercase = "ABCDEFGHJKMNPQRSTUVWXYZ"
    digits = "23456789"
    special = "!@#$%^&*"

    all_chars = lowercase + uppercase + digits + special

    # Generating a 16-character password (modern security standard)
    return ''.join(secrets.choice(all_chars) for _ in range(16))


def home(request):
    """
    Main view for the generator. Handles both initial load (GET)
    and tab switching/generation (POST).
    """
    # 1. Determine the mode (Security: default to 'password' if invalid)
    if request.method == 'POST':
        mode = request.POST.get('mode', 'password')
    else:
        mode = request.GET.get('mode', 'password')

    if mode not in ['password', 'pin']:
        mode = 'password'

    # 2. Generate the secure value
    final_password = generate_secure_code(mode)

    # 3. Render the page with the context
    context = {
        'password_generated': final_password,
        'mode': mode
    }

    return render(request, "generator/home.html", context)


def about(request):
    """View for the About page."""
    return render(request, "generator/about.html", {})