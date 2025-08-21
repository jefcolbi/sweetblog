/**
 * Article Interaction JavaScript Module
 * Handles likes, dislikes, comments, and read tracking for blog articles
 */
(function() {
    console.log('Article.js: Initializing article interaction module');
    
    // Configuration values passed from Django template
    // These are set in the HTML template before this script loads
    const articleId = window.articleId;
    const articleType = window.articleType || 'markdownarticle';
    const csrfToken = window.csrfToken || getCookie('csrftoken');
    
    console.log('Article.js: Configuration loaded', {
        articleId: articleId,
        articleType: articleType,
        csrfTokenAvailable: !!csrfToken
    });

    /**
     * Retrieves a cookie value by name
     * Used as fallback for CSRF token if not provided by template
     * @param {string} name - The cookie name to retrieve
     * @returns {string|null} The cookie value or null if not found
     */
    function getCookie(name) {
        console.log(`Article.js: Getting cookie '${name}'`);
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    console.log(`Article.js: Found cookie '${name}'`);
                    break;
                }
            }
        }
        return cookieValue;
    }

    // ====================
    // LIKE/DISLIKE FUNCTIONALITY
    // ====================
    
    // Get references to like and dislike buttons
    const likeBtn = document.getElementById('like-btn');
    const dislikeBtn = document.getElementById('dislike-btn');
    
    console.log('Article.js: Like/Dislike buttons found', {
        likeBtn: !!likeBtn,
        dislikeBtn: !!dislikeBtn
    });

    /**
     * Updates the visual state of like/dislike buttons
     * @param {boolean} liked - Whether the article is liked by current user
     * @param {boolean} disliked - Whether the article is disliked by current user
     * @param {number} likeCount - Total number of likes
     * @param {number} dislikeCount - Total number of dislikes
     */
    function updateButtonStyles(liked, disliked, likeCount, dislikeCount) {
        console.log('Article.js: Updating button styles', {
            liked, disliked, likeCount, dislikeCount
        });
        const likeSvg = likeBtn.querySelector('svg');
        const dislikeSvg = dislikeBtn.querySelector('svg');
        const likeCountSpan = document.getElementById('like-count');
        const dislikeCountSpan = document.getElementById('dislike-count');

        if (liked) {
            likeSvg.setAttribute('fill', 'gold');
            likeSvg.setAttribute('stroke', 'gold');
        } else {
            likeSvg.setAttribute('fill', 'none');
            likeSvg.setAttribute('stroke', 'currentColor');
        }

        if (disliked) {
            dislikeSvg.setAttribute('fill', 'red');
            dislikeSvg.setAttribute('stroke', 'red');
        } else {
            dislikeSvg.setAttribute('fill', 'none');
            dislikeSvg.setAttribute('stroke', 'currentColor');
        }

        // Update counts if provided
        if (likeCount !== undefined) {
            likeCountSpan.textContent = '(' + likeCount + ')';
        }
        if (dislikeCount !== undefined) {
            dislikeCountSpan.textContent = '(' + dislikeCount + ')';
        }
    }

    /**
     * Handles like/dislike actions by sending request to server
     * @param {string} action - Either 'like' or 'dislike'
     */
    function handleLikeDislike(action) {
        console.log(`Article.js: Handling ${action} action`);
        
        const url = window.likeDislikeUrl || '/sweetblog/like-dislike/';
        console.log(`Article.js: Sending ${action} request to ${url}`);
        
        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                article_id: articleId,
                article_type: articleType,
                action: action
            })
        })
        .then(response => response.json())
        .then(data => {
            console.log(`Article.js: ${action} response received`, data);
            if (data.success) {
                updateButtonStyles(data.liked, data.disliked, data.like_count, data.dislike_count);
            } else {
                console.warn(`Article.js: ${action} action failed`, data);
            }
        })
        .catch(error => {
            console.error(`Article.js: Error during ${action} action:`, error);
        });
    }

    // Attach event listeners to like/dislike buttons
    if (likeBtn) {
        likeBtn.addEventListener('click', function() {
            console.log('Article.js: Like button clicked');
            handleLikeDislike('like');
        });
    }

    if (dislikeBtn) {
        dislikeBtn.addEventListener('click', function() {
            console.log('Article.js: Dislike button clicked');
            handleLikeDislike('dislike');
        });
    }

    // ====================
    // MARK AS READ FUNCTIONALITY
    // ====================
    
    // Flag to ensure article is only marked as read once
    let hasMarkedAsRead = false;
    console.log('Article.js: Mark as read functionality initialized');

    /**
     * Marks the article as read by sending a request to the server
     * Only executes once per page load
     */
    function markArticleAsRead() {
        if (hasMarkedAsRead) {
            console.log('Article.js: Article already marked as read, skipping');
            return;
        }

        console.log('Article.js: Marking article as read');
        hasMarkedAsRead = true;

        fetch(window.markAsReadUrl || '/sweetblog/mark-as-read/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                article_id: articleId,
                article_type: articleType
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log('Article.js: Successfully marked article as read', data);
            } else {
                console.warn('Article.js: Failed to mark article as read', data);
            }
        })
        .catch(error => {
            console.error('Article.js: Error marking article as read:', error);
            hasMarkedAsRead = false; // Reset flag on error to allow retry
        });
    }

    /**
     * Checks if the article footer is visible in viewport
     * Used to determine when to mark article as read
     */
    function checkVisibility() {
        const footer = document.querySelector('article > footer');
        if (!footer) {
            console.log('Article.js: No footer found for visibility check');
            return;
        }

        const rect = footer.getBoundingClientRect();
        const viewHeight = Math.max(document.documentElement.clientHeight, window.innerHeight);

        // Check if footer is visible in viewport
        if (rect.top < viewHeight && rect.bottom > 0) {
            console.log('Article.js: Footer is visible, marking as read');
            markArticleAsRead();
            // Remove event listeners once marked as read
            window.removeEventListener('scroll', checkVisibility);
            window.removeEventListener('resize', checkVisibility);
            console.log('Article.js: Removed visibility check listeners');
        }
    }

    // Set up visibility tracking events
    window.addEventListener('scroll', checkVisibility);
    window.addEventListener('resize', checkVisibility);
    console.log('Article.js: Added scroll and resize listeners for read tracking');

    // Check initial visibility when page loads
    window.addEventListener('load', function() {
        console.log('Article.js: Page loaded, checking initial visibility');
        checkVisibility();
    });

    // Also check after a short delay to handle dynamic content loading
    setTimeout(function() {
        console.log('Article.js: Delayed visibility check (1s)');
        checkVisibility();
    }, 1000);

    // ====================
    // COMMENT SYSTEM
    // ====================
    
    console.log('Article.js: Initializing comment system');
    
    /**
     * Submit a new top-level comment
     * Global function accessible from HTML onclick handlers
     */
    window.submitComment = function() {
        console.log('Article.js: submitComment called');
        const content = document.getElementById('main-comment-content').value.trim();

        if (!content) {
            console.warn('Article.js: Empty comment, showing alert');
            alert('Please write a comment before submitting.');
            return;
        }
        
        console.log('Article.js: Submitting comment with content length:', content.length);

        // Disable the form while submitting
        const textarea = document.getElementById('main-comment-content');
        const button = textarea.nextElementSibling;
        textarea.disabled = true;
        button.disabled = true;
        button.textContent = 'Posting...';

        // Send comment to server
        fetch(window.submitCommentUrl || '/sweetblog/submit-comment/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                article_id: articleId,
                article_type: articleType,
                content: content
            })
        })
        .then(response => response.json())
        .then(data => {
            console.log('Article.js: Comment submission response:', data);
            if (data.success) {
                // Clear the form
                textarea.value = '';
                console.log('Article.js: Comment form cleared');

                // Add the new comment to the page
                addCommentToPage(data.comment);

                // Update comment count
                updateCommentCount(1);
            } else {
                console.error('Article.js: Comment submission failed:', data);
                alert('Error: ' + (data.error || 'Failed to post comment'));
            }
        })
        .catch(error => {
            console.error('Error posting comment:', error);
            alert('Failed to post comment. Please try again.');
        })
        .finally(() => {
            // Re-enable the form
            textarea.disabled = false;
            button.disabled = false;
            button.textContent = 'Post Comment';
        });
    };

    /**
     * Show reply form for a specific comment
     * Global function accessible from HTML onclick handlers
     * @param {number} formId - ID of the comment to reply to
     * @param {number} targetParentId - ID of the parent comment for threading
     */
    window.showReplyForm = function(formId, targetParentId) {
        console.log('Article.js: showReplyForm called', { formId, targetParentId });
        // Hide all other reply forms
        const allForms = document.querySelectorAll('[id^="reply-form-"]');
        console.log(`Article.js: Hiding ${allForms.length} reply forms`);
        allForms.forEach(form => {
            form.style.display = 'none';
        });

        // Show this reply form
        const replyForm = document.getElementById('reply-form-' + formId);
        if (replyForm) {
            replyForm.style.display = 'block';
            console.log(`Article.js: Showed reply form ${formId}`);
            
            const textarea = document.getElementById('reply-content-' + formId);
            if (textarea) {
                textarea.focus();
                console.log('Article.js: Focused on reply textarea');
            }
        } else {
            console.error(`Article.js: Reply form not found for ID ${formId}`);
        }

        // Store the target parent ID for submission
        window.currentReplyTarget = targetParentId;
        window.currentReplyForm = formId;
    };

    /**
     * Hide reply form for a specific comment
     * Global function accessible from HTML onclick handlers
     * @param {number} commentId - ID of the comment whose reply form to hide
     */
    window.hideReplyForm = function(commentId) {
        console.log('Article.js: hideReplyForm called for comment', commentId);
        const replyForm = document.getElementById('reply-form-' + commentId);
        if (replyForm) {
            replyForm.style.display = 'none';
            const textarea = document.getElementById('reply-content-' + commentId);
            if (textarea) {
                textarea.value = '';
            }
        }
    };

    /**
     * Submit a reply to an existing comment
     * Global function accessible from HTML onclick handlers
     * @param {number} formId - ID of the comment form being submitted
     */
    window.submitReply = function(formId) {
        console.log('Article.js: submitReply called for form', formId);
        const content = document.getElementById('reply-content-' + formId).value.trim();
        const targetParentId = window.currentReplyTarget || formId;

        if (!content) {
            console.warn('Article.js: Empty reply, showing alert');
            alert('Please write a reply before submitting.');
            return;
        }
        
        console.log('Article.js: Submitting reply', {
            formId, targetParentId, contentLength: content.length
        });

        // Disable the form while submitting
        const textarea = document.getElementById('reply-content-' + formId);
        const buttons = textarea.nextElementSibling.querySelectorAll('button');
        textarea.disabled = true;
        buttons[0].disabled = true;
        buttons[0].textContent = 'Posting...';
        buttons[1].disabled = true;

        // Send reply to server
        fetch(window.submitCommentUrl || '/sweetblog/submit-comment/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                article_id: articleId,
                article_type: articleType,
                content: content,
                parent_id: targetParentId
            })
        })
        .then(response => response.json())
        .then(data => {
            console.log('Article.js: Reply submission response:', data);
            if (data.success) {
                // Hide the reply form
                hideReplyForm(formId);

                // Add the new reply to the page
                addReplyToPage(data.comment, targetParentId);

                // Update comment count
                updateCommentCount(1);
                console.log('Article.js: Reply successfully added');
            } else {
                console.error('Article.js: Reply submission failed:', data);
                alert('Error: ' + (data.error || 'Failed to post reply'));
            }
        })
        .catch(error => {
            console.error('Error posting reply:', error);
            alert('Failed to post reply. Please try again.');
        })
        .finally(() => {
            // Re-enable the form
            textarea.disabled = false;
            buttons[0].disabled = false;
            buttons[0].textContent = 'Post Reply';
            buttons[1].disabled = false;
        });
    };

    /**
     * Add a new comment to the page DOM
     * @param {Object} comment - Comment data from server
     */
    function addCommentToPage(comment) {
        console.log('Article.js: Adding comment to page', comment);
        const container = document.getElementById('comments-container');

        // Remove "no comments" message if it exists
        const noComments = container.querySelector('p');
        if (noComments && noComments.textContent.includes('No comments yet')) {
            noComments.remove();
            console.log('Article.js: Removed "no comments" message');
        }

        // Create comment HTML
        const commentDiv = document.createElement('div');
        commentDiv.className = 'comment';
        commentDiv.dataset.commentId = comment.id;
        commentDiv.dataset.level = comment.level || 0;
        commentDiv.style.marginLeft = ((comment.level || 0) * 2) + 'rem';
        commentDiv.style.marginBottom = '1rem';
        commentDiv.style.padding = '1rem';
        commentDiv.style.borderLeft = '2px solid #e0e0e0';

        commentDiv.innerHTML = `
            <div style="font-size: 0.9rem; color: #666; margin-bottom: 0.5rem;">
                <strong>${comment.username}</strong> •
                <span>${comment.created_at}</span>
            </div>
            <div style="margin-bottom: 0.5rem; line-height: 1.5;">
                ${comment.content.replace(/\n/g, '<br>')}
            </div>
            <button class="reply-btn"
                    onclick="showReplyForm(${comment.id})"
                    style="font-size: 0.9rem; padding: 0.25rem 0.75rem; background: none; border: 1px solid #ccc; border-radius: 3px; cursor: pointer;">
                Reply
            </button>
            <div id="reply-form-${comment.id}" style="display: none; margin-top: 1rem;">
                <textarea id="reply-content-${comment.id}"
                          placeholder="Write a reply..."
                          style="width: 100%; min-height: 80px; padding: 0.5rem; border: 1px solid #ccc; border-radius: 5px; resize: vertical;"></textarea>
                <div style="margin-top: 0.5rem;">
                    <button onclick="submitReply(${comment.id})"
                            style="padding: 0.25rem 0.75rem; background: #007bff; color: white; border: none; border-radius: 3px; cursor: pointer; margin-right: 0.5rem;">
                        Post Reply
                    </button>
                    <button onclick="hideReplyForm(${comment.id})"
                            style="padding: 0.25rem 0.75rem; background: #6c757d; color: white; border: none; border-radius: 3px; cursor: pointer;">
                        Cancel
                    </button>
                </div>
            </div>
        `;

        // Add to container at the beginning (newest first)
        container.insertBefore(commentDiv, container.firstChild);
        console.log('Article.js: Comment added to DOM');
    }

    /**
     * Add a reply to an existing comment (Facebook-style threading)
     * @param {Object} reply - Reply data from server
     * @param {number} parentId - ID of the parent comment
     */
    function addReplyToPage(reply, parentId) {
        console.log('Article.js: Adding reply to page', { reply, parentId });
        const parentComment = document.querySelector(`[data-comment-id="${parentId}"]`);
        const commentReplyForm = document.getElementById(`reply-form-${parentId}`);

        console.log(parentComment);
        console.log(commentReplyForm);

        // Create reply HTML
        const replyDiv = document.createElement('div');
        replyDiv.className = 'comment';
        replyDiv.dataset.commentId = reply.id;
        replyDiv.dataset.level = reply.level || 1;
        replyDiv.style.marginLeft = '2rem';
        replyDiv.style.marginBottom = '1rem';
        replyDiv.style.marginTop = '1rem';
        replyDiv.style.padding = '1rem';
        replyDiv.style.borderLeft = '2px solid #e0e0e0';

        replyDiv.innerHTML = `
            <div style="font-size: 0.9rem; color: #666; margin-bottom: 0.5rem;">
                <strong>${reply.username}</strong> •
                <span>${reply.created_at}</span>
            </div>
            <div style="margin-bottom: 0.5rem; line-height: 1.5;">
                ${reply.content.replace(/\n/g, '<br>')}
            </div>
        `;

        // Insert after the last reply
        parentComment.insertBefore(replyDiv, commentReplyForm);
        console.log('Article.js: Reply inserted after last sibling');
    }

    /**
     * Update the comment count display in the UI
     * @param {number} increment - Number to add to current count
     */
    function updateCommentCount(increment) {
        console.log('Article.js: Updating comment count by', increment);
        const h2 = document.querySelector('section h2');
        if (h2 && h2.textContent.includes('Comments')) {
            const match = h2.textContent.match(/\((\d+)\)/);
            if (match) {
                const currentCount = parseInt(match[1]);
                const newCount = currentCount + increment;
                h2.textContent = `Comments (${newCount})`;
                console.log('Article.js: Comment count updated to', newCount);
            } else {
                console.warn('Article.js: Could not parse comment count from heading');
            }
        } else {
            console.warn('Article.js: Comments heading not found');
        }
    }
    
    console.log('Article.js: Article interaction module initialization complete');
})();