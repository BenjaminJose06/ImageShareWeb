/**
 * Waits until the DOM is fully loaded before executing the script.
 */
document.addEventListener("DOMContentLoaded", function () {

    /**
     * Sets a timeout to remove flash messages after 3 seconds.
     */
    setTimeout(function () {
        
        // Select all elements with the class "flash-message" (flashed alerts)
        let messages = document.querySelectorAll(".flash-message");

        /**
         * Loop through each flash message and gradually fade it out.
         */
        messages.forEach(function (message) {
            message.style.opacity = "0"; // Start fading effect
            
            // After 1 second (so once faded out), completely remove the message
            setTimeout(() => message.remove(), 1000);
        });

    }, 3000); // Flash messages remain visible for 3 seconds before disappearing
});
