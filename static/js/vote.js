/**
 * Handles the voting functionality for image items.
 * Allows users to upvote or downvote images dynamically.
 * Applies the correct styling and updates vote count without reloading the page.
 */

document.addEventListener("DOMContentLoaded", function () {
    // Iterate over each image item on the page
    document.querySelectorAll(".image-item").forEach(image => {
    const imageId = image.getAttribute("data-image-id"); // Get image ID
    const userVote = image.getAttribute("data-user-vote"); // Retrieve stored user vote status

        // Select the upvote and downvote buttons for the image
        const upvoteButton = image.querySelector(`.vote-btn[data-vote-type="upvote"]`);
        const downvoteButton = image.querySelector(`.vote-btn[data-vote-type="downvote"]`);
        const voteCount = document.getElementById(`vote-count-${imageId}`);

        if (!upvoteButton || !downvoteButton || !voteCount) return; // Ensure all elements exist before proceeding

        // Apply saved vote styles when the page loads
        if (userVote === "upvote") {
            upvoteButton.classList.add("upvoted");
        } else if (userVote === "downvote") {
            downvoteButton.classList.add("downvoted");
        }

        // Attach event listeners to both vote buttons (upvote & downvote)
        [upvoteButton, downvoteButton].forEach(button => {
            button.addEventListener("click", function () {
                const voteType = this.getAttribute("data-vote-type"); // Get vote type (upvote/downvote)

                // Send the vote request to the backend
                fetch(`/vote/${imageId}/${voteType}`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-Requested-With": "XMLHttpRequest"
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Update the displayed vote count
                        voteCount.textContent = data.new_vote_count;

                        // Reset button styles to remove previous selection
                        upvoteButton.classList.remove("upvoted");
                        downvoteButton.classList.remove("downvoted");

                        // Apply the correct highlight based on the new vote selection
                        if (data.user_vote === "upvote") {
                            upvoteButton.classList.add("upvoted");
                        } else if (data.user_vote === "downvote") {
                            downvoteButton.classList.add("downvoted");
                        }
                    }
                })
                .catch(error => console.error("Error:", error)); // Handle request errors
            });
        });
    });
});
