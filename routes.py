import io
from io import BytesIO
import qrcode
from datetime import datetime
from PIL import Image as PILImage
from flask import (
    Flask, render_template, redirect, url_for, flash, request,
    Response, send_file, jsonify
)
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user
)
from werkzeug.utils import secure_filename

from models import db, User, Image, Vote, Follower, Comment
from forms import (
    RegistrationForm, LoginForm, RequestResetForm,
    ResetPasswordForm, ChangeEmailForm, ChangePasswordForm
)


app = Flask(__name__)

app.config["SECRET_KEY"] = "thisdoesntmeananything"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


from app import send_email


# Load user from the database using Flask-Login
@login_manager.user_loader
def load_user(user_id):
    """
    Loads a user based on their user ID.

    Args:
        user_id (int): The ID of the user to be loaded.

    Returns:
        User: The user object if found, otherwise None.
    """
    return User.query.get(int(user_id))


# Route for the homepage
@app.route('/')
def index():
    """
    Renders the homepage.

    Returns:
        Template: Renders the 'index.html' template.
    """
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Handles user registration.

    - Validates user input.
    - Checks if the username or email already exists.
    - Creates a new user and stores it in the database.
    - Sends a verification email.
    - Redirects to the login page upon successful registration.

    Returns:
        Template: Renders 'register.html' with the registration form.
    """
    form = RegistrationForm()
    
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data

        # Check if the username is already taken
        if User.query.filter_by(username=username).first():
            flash('Username already taken. Please choose another.', 'danger')
            return redirect(url_for('register'))
        
        # Check if the email is already registered
        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please use a different email.', 'danger')
            return redirect(url_for('register'))

        # Create a new user and hash the password
        user = User(username=username, email=email, is_verified=False)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # Generate verification token
        token = user.get_reset_token()
        verification_link = url_for('verify_email', token=token, _external=True)

        # Send verification email
        subject = "Verify Your Email"
        body = f"""
        Hello {user.username},

        Click the link below to verify your email:

        {verification_link}

        If you did not request this, ignore this email.
        """
        email_sent = send_email(user.email, subject, body)

        if email_sent:
            flash('Registration successful! Please check your email to verify your account.', 'success')
        else:
            flash('Registration successful, but email failed to send.', 'danger')

        return redirect(url_for('login'))

    return render_template('register.html', form=form)


# Route to verify a user's email using a unique token
@app.route('/verify_email/<token>')
def verify_email(token):
    """
    Verifies the user's email using the provided token.

    Parameters:
    token (str): The verification token sent to the user's email.

    Returns:
    Redirect: Redirects to the login page if verification is successful, 
              otherwise redirects to registration with an error message.
    """
    user = User.verify_reset_token(token)
    if not user:
        flash('Invalid or expired verification link.', 'danger')
        return redirect(url_for('register'))  # Redirect if token is invalid

    # Mark user as verified and commit changes to the database
    user.is_verified = True
    db.session.commit()
    
    flash('Your email has been verified! You can now log in.', 'success')
    return redirect(url_for('login'))

@app.route('/verify_new_email/<token>/<new_email>')
@login_required
def verify_new_email(token, new_email):
    """
    Verifies and updates the user's email after they request an email change.
    """
    user = User.verify_reset_token(token)
    if not user:
        flash('Invalid or expired token', 'danger')
        return redirect(url_for('account'))

    # Update email
    user.email = new_email
    db.session.commit()

    flash('Your email has been updated successfully!', 'success')
    return redirect(url_for('account'))


# Route for user login
@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handles user login by verifying credentials.

    Returns:
    - On successful login:
        - Redirects superusers to the superuser dashboard.
        - Redirects regular users to their account page.
    - On failure:
        - Displays an error message and reloads the login page.
    """
    form = LoginForm()

    if form.validate_on_submit():
        print("Form Submitted!") 
        print(f"Email/Username: {form.email_or_username.data}")  
        print(f"Password: {form.password.data}")

        # Check if the provided email or username exists in the database
        user = User.query.filter(
            (User.email == form.email_or_username.data) | 
            (User.username == form.email_or_username.data)
        ).first()

        if user:
            print(f"Found User: {user.username}") 

        # Validate user credentials
        if user and user.check_password(form.password.data):
            if not user.is_verified:
                flash('Please verify your email before logging in.', 'warning')
                return redirect(url_for('login'))  # Prevent login if not verified

            login_user(user)  # Log the user in
            flash('Login successful!', 'success')

            # Redirect superusers to their dashboard, others to their account
            return redirect(url_for('superuser_dashboard') if user.is_superuser else url_for('account'))

        flash('Invalid email/username or password', 'danger')

    return render_template('login.html', form=form)  # Render login page



# Route to request a password reset
@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    form = RequestResetForm()

    if form.validate_on_submit():
        # Check if the email exists in the database
        user = User.query.filter_by(email=form.email.data).first()

        if user:
            # Generate a reset token and email reset link
            token = user.get_reset_token()
            reset_link = url_for('reset_password', token=token, _external=True)
            email_body = f"Hello {user.username},\n\nClick the link below to reset your password:\n\n{reset_link}\n\nIf you did not request this, ignore this email."
            
            # Send reset email
            send_email(user.email, "Password Reset Request", email_body)

            flash('A password reset email has been sent.', 'success')
        else:
            flash('No account found with that email.', 'danger')

        return redirect(url_for('login'))

    # Render the password reset request form
    return render_template('reset_password_request.html', form=form)


# Route to reset password using a token
@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    # Verify the reset token
    user = User.verify_reset_token(token)
    if not user:
        flash('Invalid or expired token', 'danger')
        return redirect(url_for('reset_password_request'))

    form = ResetPasswordForm()

    if form.validate_on_submit():
        # Update user's password and commit changes
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset! You can now log in.', 'success')
        return redirect(url_for('login'))

    # Render the password reset form
    return render_template('reset_password.html', form=form)


# Route to change user's email
@app.route('/change_email', methods=['GET', 'POST'])
@login_required
def change_email():
    form = ChangeEmailForm()

    if form.validate_on_submit():
        # Check if the new email is already in use
        if User.query.filter_by(email=form.new_email.data).first():
            flash('This email is already in use.', 'danger')
            return redirect(url_for('account'))

        # Generate a verification token and send confirmation email
        token = current_user.get_reset_token()
        verification_link = url_for('verify_new_email', token=token, new_email=form.new_email.data, _external=True)
        email_body = f"Hello {current_user.username},\n\nClick the link below to confirm your new email:\n\n{verification_link}\n\nIf you did not request this, ignore this email."
        send_email(form.new_email.data, "Confirm Your New Email", email_body)

        flash('A confirmation email has been sent to your new address.', 'success')
        return redirect(url_for('account'))

    # Render the change email form
    return render_template('change_email.html', form=form)

# Route to change user's password
@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        # Verify the current password before allowing a change
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect.', 'danger')
            return redirect(url_for('account'))

        # Update password and save changes
        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash('Your password has been updated!', 'success')
        return redirect(url_for('account'))

    # Render the change password form
    return render_template('change_password.html', form=form)


# Route to log out the user
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))


# Route for user account page
@app.route('/account')
@login_required
def account():
    return render_template('account.html')

@app.route('/superuser_dashboard', methods=['GET'])
@login_required
def superuser_dashboard():
    if not current_user.is_superuser:
        flash("Access Denied!", "danger")
        return redirect(url_for('index'))

    selected_category = request.args.get('category', 'all')
    categories = ["Nature", "Art", "Technology", "Memes", "Photography"]

    if selected_category == 'all':
        images = Image.query.filter(Image.moderation_status.in_(["pending", "approved"])).all()
    else:
        images = Image.query.filter(
            Image.moderation_status.in_(["pending", "approved"]),
            Image.category == selected_category
        ).all()

    return render_template('superuser_dashboard.html', images=images, selected_category=selected_category, categories=categories)


# Route for uploading image
@app.route('/upload_image', methods=['GET', 'POST'])
@login_required
def upload_image():
    from forms import UploadImageForm
    form = UploadImageForm()
    if form.validate_on_submit():
        name = form.name.data
        file = form.image.data

        # Open and process the uploaded image
        img = PILImage.open(file)
        img = img.resize((64, 64), PILImage.LANCZOS)
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        img_io = io.BytesIO()
        img.save(img_io, format="PNG")
        img_io.seek(0)
        image_data = img_io.read()

        # Create new image entry and save to database
        image = Image(name=name, image_data=image_data, user_id=current_user.id)
        db.session.add(image)
        db.session.commit()

        flash('Image uploaded successfully!', 'success')
        return redirect(url_for('upload_image'))

    return render_template('upload_image.html', form=form)



# Route to retrieve an image from the database
@app.route('/image/<int:image_id>')
def get_image(image_id):
    # Fetch image from database, or return 404 if not found
    image = Image.query.get_or_404(image_id)

    # Check if image contains image data
    if not image.image_data:
        flash("Image not found!", "danger")
        return redirect(url_for('index'))

    # Return the image data as a response with PNG format
    return Response(image.image_data, mimetype='image/png')   


# Route for superuser to moderate an image
@app.route('/moderate_image/<int:image_id>', methods=['POST'])
@login_required
def moderate_image(image_id):
    categories = ["Nature", "Art", "Technology", "Memes", "Photography"]
    # Ensure only the superuser can access this function
    if not current_user.is_superuser:
        flash("Access Denied!", "danger")
        return redirect(url_for('index'))

    # Fetch the image from the database, or return 404 if not found
    image = Image.query.get_or_404(image_id)

    # Ensure the image has a valid moderation status before modifying it
    if image.moderation_status not in ["pending", "approved", "unmoderated"]:
        flash("Only images that have been requested for moderation can be changed!", "danger")
        return redirect(url_for('edit_images'))

    # Get the new moderation status and category from the form
    new_status = request.form.get('status')
    new_category = request.form.get('category')

    # Validate and update the image's moderation status
    if new_status in ["approved", "pending", "unmoderated"]:
        image.moderation_status = new_status

        # Generate a unique number if the image is approved and doesn't already have one
        if new_status == "approved" and not image.unique_number:
            image.unique_number = image.generate_unique_number()

        # If an archived image is unmoderated, unarchive it
        if image.is_archived and new_status == "unmoderated":
            image.is_archived = False
            flash(f"Image '{image.name}' was unmoderated and has been unarchived.", "success")
    else:
        flash("Invalid status update!", "danger")
        return redirect(url_for('edit_images'))

    # Validate and update the image's category
    if new_category in categories:
        image.category = new_category
    else:
        flash("Invalid category!", "danger")
        return redirect(url_for('edit_images'))

    # Commit changes to the database
    db.session.commit()
    flash(f"Image '{image.name}' updated to {new_status}, Category: {new_category}.", "success")
    
    return redirect(url_for('edit_images'))

# Route for superuser to toggle archive status of an image
@app.route('/toggle_archive/<int:image_id>', methods=['POST'])
@login_required
def toggle_archive(image_id):
    # Ensure only the superuser can access this function
    if not current_user.is_superuser:
        flash("Access Denied!", "danger")
        return redirect(url_for('index'))

    # Fetch image from database, or return 404 if not found
    image = Image.query.get_or_404(image_id)

    # Toggle the archive status
    if image.is_archived:
        image.is_archived = False
        flash(f"Image '{image.name}' has been unarchived.", "success")
    else:
        image.is_archived = True
        flash(f"Image '{image.name}' has been archived.", "success")

    # Commit changes to the database
    db.session.commit()

    # Redirect back to the referring page or default to the archived images page
    return redirect(request.referrer or url_for('archived_images'))  


# Route for users to toggle archive status of their own image
@app.route('/toggle_artist_archive/<int:image_id>', methods=['POST'])
@login_required
def toggle_artist_archive(image_id):
    # Fetch image from database, or return 404 if not found
    image = Image.query.get_or_404(image_id)

    # Ensure only the owner of the image can toggle its archive status
    if image.user_id != current_user.id:  
        flash("Access Denied!", "danger")
        return redirect(url_for('account'))

    # Toggle the archive status for the user
    image.artist_archived = not image.artist_archived  
    db.session.commit()

    # Display flash message to confirm the change
    status_text = "archived" if image.artist_archived else "unarchived"
    flash(f"Image '{image.name}' has been {status_text}.", "success")

    # Redirect back to the referring page or default to the user's archived images page
    return redirect(request.referrer or url_for('artist_archived_images')) 


# Route to display the user's archived images
@app.route('/artist_archived_images', methods=['GET'])
@login_required
def artist_archived_images():
    return render_template('artist_archived_images.html')


# Route to allow a user to request moderation for their image
@app.route('/request_moderation/<int:image_id>', methods=['POST'])
@login_required
def request_moderation(image_id):
    image = Image.query.get_or_404(image_id)

    # Ensure only the owner of the image can request moderation
    if image.user_id != current_user.id:  
        flash("Access Denied!", "danger")
        return redirect(url_for('account'))

    # Change moderation status to 'pending' if it was unmoderated
    if image.moderation_status == "unmoderated":
        image.moderation_status = "pending"
        db.session.commit()
        flash(f"Image '{image.name}' has been sent for moderation.", "success")

    return redirect(request.referrer or url_for('account'))


# Route for superuser to edit and moderate images
@app.route('/edit_images', methods=['GET'])
@login_required
def edit_images():
    if not current_user.is_superuser:
        flash("Access Denied!", "danger")
        return redirect(url_for('index'))

    selected_category = request.args.get('category', 'all')
    categories = ["Nature", "Art", "Technology", "Memes", "Photography"]

    if selected_category == 'all':
        images = Image.query.filter(Image.moderation_status.in_(["pending", "approved", "unmoderated"])).all()
    else:
        images = Image.query.filter(Image.moderation_status.in_(["pending", "approved", "unmoderated"]),
                                    Image.category == selected_category).all()

    return render_template('edit_images.html', images=images, selected_category=selected_category, categories=categories)


# Route to display archived images (only accessible by superuser)
@app.route('/archived_images', methods=['GET'])
@login_required
def archived_images():
    if not current_user.is_superuser:
        flash("Access Denied!", "danger")
        return redirect(url_for('index'))

    selected_category = request.args.get('category', 'all')
    categories = ["Nature", "Art", "Technology", "Memes", "Photography"]

    if selected_category == 'all':
        images = Image.query.filter_by(is_archived=True).all()
    else:
        images = Image.query.filter_by(is_archived=True, category=selected_category).all()

    return render_template('archived_images.html', images=images, selected_category=selected_category, categories=categories)


@app.route('/generate_qr/<int:image_id>')
def generate_qr(image_id):
    """ Generates a QR code for an image if it is approved and has a unique number. """

    # Fetch the image by ID or return a 404 error if not found
    image = Image.query.get_or_404(image_id)

    # Ensure the image is approved before generating a QR code
    if image.moderation_status != "approved":
        flash("QR Code is only available for moderated images.", "danger")
        return redirect(url_for('view_all_images'))

    # Ensure the image has a unique number assigned
    if not image.unique_number:
        flash("This image does not have a unique number yet.", "danger")
        return redirect(url_for('view_all_images'))

    # Create a QR code instance with error correction and size settings
    qr = qrcode.QRCode(
        version=1,  
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=5,  
        border=2  
    )

    # Add the image's unique number to the QR code
    qr.add_data(f"Image ID: {image.unique_number}")
    qr.make(fit=True)

    # Generate the QR code image
    img = qr.make_image(fill="black", back_color="white")

    # Save the QR code image in memory as a PNG
    img_io = BytesIO()
    img.save(img_io, "PNG")
    img_io.seek(0)  # Reset the stream position

    # Return the QR code as a downloadable image response
    return send_file(img_io, mimetype='image/png')



# Route to display a user's active images
@app.route('/user_active_images', methods=['GET'])
@login_required
def user_active_images():
    return render_template('active_images.html')


# Route to display a user's moderated images
@app.route('/user_moderated_images', methods=['GET'])
@login_required
def user_moderated_images():
    return render_template('moderated_images.html')


# Route to display all images to authenticated users
@app.route("/view_all_images")
@login_required
def view_all_images():
    selected_category = request.args.get('category', 'all')
    categories = ["Nature", "Art", "Technology", "Memes", "Photography"]

    if selected_category == 'all':
        images = Image.query.all()
    else:
        images = Image.query.filter_by(category=selected_category).all()

    user_votes = {vote.image_id: vote.vote_type for vote in Vote.query.filter_by(user_id=current_user.id).all()}

    return render_template("view_all_images.html", images=images, user_votes=user_votes, selected_category=selected_category, categories=categories)


# Allowed file types for image uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Function to check if a file has a valid extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Route to handle voting on an image
@app.route("/vote/<int:image_id>/<vote_type>", methods=["POST"])
@login_required
def vote(image_id, vote_type):
    image = Image.query.get_or_404(image_id)

    # Find existing vote from the current user
    existing_vote = Vote.query.filter_by(user_id=current_user.id, image_id=image_id).first()

    if existing_vote:
        if existing_vote.vote_type == vote_type:
            # If the user clicks the same vote again, remove the vote
            db.session.delete(existing_vote)
            db.session.commit()

            # Update vote count after removing the vote
            image.vote_count = Vote.query.filter_by(image_id=image_id, vote_type="upvote").count() - \
                                 Vote.query.filter_by(image_id=image_id, vote_type="downvote").count()

            db.session.commit()
            return jsonify(success=True, new_vote_count=image.vote_count, user_vote=None)
        else:
            # If switching votes, update vote type
            existing_vote.vote_type = vote_type
    else:
        # If no previous vote, create a new one
        new_vote = Vote(user_id=current_user.id, image_id=image_id, vote_type=vote_type)
        db.session.add(new_vote)

    # Update the vote count based on the new voting state
    image.vote_count = Vote.query.filter_by(image_id=image_id, vote_type="upvote").count() - \
                         Vote.query.filter_by(image_id=image_id, vote_type="downvote").count()

    db.session.commit()
    return jsonify(success=True, new_vote_count=image.vote_count, user_vote=vote_type)

# Route for resetting votes on an image (Superuser only)
@app.route('/reset_votes/<int:image_id>', methods=['POST'])
@login_required
def reset_votes(image_id):
    if not current_user.is_superuser:
        flash("Access Denied!", "danger")
        return redirect(url_for('index'))

    image = Image.query.get_or_404(image_id)
    reset_reason = request.form.get("reset_reason")

    if not reset_reason:
        flash("You must provide a reason for resetting votes.", "danger")
        return redirect(url_for('edit_images'))

    # Reset the vote count and store the reset reason
    image.vote_count = 0
    image.last_reset_date = datetime.utcnow()
    image.last_reset_reason = reset_reason

    # Remove all votes associated with this image
    Vote.query.filter_by(image_id=image.id).delete()

    db.session.commit()
    flash(f"Votes for '{image.name}' have been reset to 0. Users can now vote again.", "success")
    return redirect(url_for('edit_images'))


# Route to allow guests to browse moderated images by category
@app.route('/guest_view', methods=['GET'])
def guest_view():
    selected_category = request.args.get('category', 'all')
    categories = ["Nature", "Art", "Technology", "Memes", "Photography"]

    if selected_category == 'all':
        images = Image.query.filter(Image.moderation_status == "approved").all()
    else:
        images = Image.query.filter(Image.moderation_status == "approved", Image.category == selected_category).all()

    return render_template('guest_view.html', images=images, selected_category=selected_category, categories=categories)


# Route to display the profile of the logged-in user
@app.route('/profile')
@login_required
def profile():
    # Fetch list of users following the current user
    followers = [follower.follower for follower in current_user.followers_list]

    # Retrieve the user's most upvoted approved image
    most_upvoted_image = (
        Image.query.filter_by(user_id=current_user.id, moderation_status="approved")
        .order_by(Image.vote_count.desc())
        .first()
    )

    return render_template('profile.html', user=current_user, followers=followers, most_upvoted_image=most_upvoted_image)


# Route to follow a user
@app.route('/follow/<int:user_id>', methods=['POST'])
@login_required
def follow_user(user_id):
    user = User.query.get_or_404(user_id)

    # Ensure the user is not following themselves and that the user is not a superuser
    if user != current_user and not user.is_superuser:
        follow = Follower(follower_id=current_user.id, followed_id=user.id)  
        db.session.add(follow)
        db.session.commit()
        flash(f"You are now following {user.username}.", "success")

    return redirect(url_for('public_profile', user_id=user.id)) 


# Route to unfollow a user
@app.route('/unfollow/<int:user_id>', methods=['POST'])
@login_required
def unfollow_user(user_id):
    user = User.query.get_or_404(user_id)

    # Check if the user is already following the user
    follow = Follower.query.filter_by(follower_id=current_user.id, followed_id=user.id).first()  
    if follow:
        db.session.delete(follow)
        db.session.commit()
        flash(f"You have unfollowed {user.username}.", "success")

    return redirect(url_for('public_profile', user_id=user.id))  


# Route to display a public profile of a user
@app.route('/profile/<int:user_id>')
def public_profile(user_id):
    user = User.query.get_or_404(user_id)

    # Retrieve list of followers for the user
    followers = [follower.follower for follower in user.followers_list]

    # Fetch the user's most upvoted approved image
    most_upvoted_image = (
        Image.query.filter_by(user_id=user.id, moderation_status="approved")
        .order_by(Image.vote_count.desc())
        .first()
    )

    # Determine if the current user follows the user
    following = set()
    if current_user.is_authenticated:
        following = {follow.followed_id for follow in current_user.following}

    return render_template('profile.html', user=user, followers=followers, most_upvoted_image=most_upvoted_image, following=following)


# Route to view and post comments on an image
@app.route('/image/<int:image_id>/comments', methods=['GET', 'POST'])
def view_comments(image_id):
    image = Image.query.get_or_404(image_id)

    # Ensure comments are only available for moderated image
    if image.moderation_status != "approved":
        flash("Comments are only available for moderated images.", "danger")
        return redirect(url_for('view_all_images'))

    # Retrieve all comments for the image, sorted by latest first
    comments = Comment.query.filter_by(image_id=image.id).order_by(Comment.timestamp.desc()).all()

    if request.method == 'POST':
        content = request.form.get('content')

        # Ensure the comment is not empty
        if not content.strip():
            flash("Comment cannot be empty.", "danger")
            return redirect(url_for('view_comments', image_id=image.id))

        # Add a new comment to the database
        new_comment = Comment(content=content, user_id=current_user.id, image_id=image.id)
        db.session.add(new_comment)
        db.session.commit()
        flash("Comment added!", "success")

        return redirect(url_for('view_comments', image_id=image.id))

    return render_template('comments.html', image=image, comments=comments)


# Route to delete a comment (Only accessible to superusers)
@app.route('/delete_comment/<int:comment_id>', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)

    # Ensure only superusers can delete comments
    if not current_user.is_superuser:
        flash("Only superusers can delete comments.", "danger")
        return redirect(url_for('view_comments', image_id=comment.image_id))

    # Delete the comment from the database
    db.session.delete(comment)
    db.session.commit()
    flash("Comment deleted successfully.", "success")

    return redirect(url_for('view_comments', image_id=comment.image_id))


# Run the Flask application
if __name__ == '__main__':
    app.run(debug=True)
