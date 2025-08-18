# Authentication in Sweetblog

## Idea

The authentication must be very lightweight and passwordless.

At the bottom of every page (in base template), We should have a footer which shows the current connected user 
and a link (with a `next` query param to back to the current page) to update his informations.  
If the user is not connected, we should display a link (with a `next` query param to back to the current page) to connect.

## Implementation

### Connection page

The connection page must show a form with 1 field "email".

When the user submits his email we check if that user exists, if it exists we check if it has already 
been linked with the current device. If it has not been linked, we create a user with the submitted email 
and with username being random value generated with generate_username, 
then send him a code to his email and save the code sent
in a model named TempCode. We redirect to the page where the user can enter the code and we don't forget 
to propagrate the query param `next` value. If the user is already linked, we log the user and redirect 
him to the query param `next` path.

### Code page

The code page must show a form with 2 fields "email" and "code".

When the user submits the form, we check if the email and code match. If they do, 
we link the user with the current device and redirect to he query param `next` path.

### Profile page

The profile page will show 3 fields:

- email: a readonly field
- username: which is modifiable
- receive_newsletter: which is checkbox if wether or not the user wants to receive the newsletter. 
This value is retrieved and stored from a model SweetblogProfile which is linked using OneToOneField to the User model.

## Testing

All the pages, forms and logic must be carefully written and tested. No exception.

## To pay attention

You show include the `next` query param to any link you build for the authentication pages so that the user
can back to the refering page after completion.