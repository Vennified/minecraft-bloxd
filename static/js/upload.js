document.addEventListener('DOMContentLoaded', function () {
    const uploadFileBox = document.getElementById('uploadfile');
    const fileInput = document.getElementById('fileInput');
    const progressBar = document.getElementById('progress-bar');
    const progressStatus = document.getElementById('progress-status');
    const progressBarContainer = document.getElementById('progress-bar-container');
    const downloadLink = document.getElementById('downloadLink');
    const downloadButton = document.getElementById('downloadButton');
    const resourcePackText = document.querySelector('.resource-pack-text'); // Select the resource pack text
    const centerIcon = document.querySelector('.center-icon'); // Select the center icon

    // Trigger file input when the dashed box (#uploadfile) is clicked
    uploadFileBox.addEventListener('click', function () {
        fileInput.click();
    });

    // Handle file input change and trigger the upload
    fileInput.addEventListener('change', async function (event) {
        const file = event.target.files[0];
        if (file) {
            // Hide the resource pack text and the center icon
            resourcePackText.style.display = 'none';
            centerIcon.style.display = 'none';

            const formData = new FormData();
            formData.append('file', file);

            try {
                // Show progress bar and status
                progressBarContainer.style.display = 'block';
                progressStatus.style.display = 'block';
                progressStatus.textContent = 'Uploading (0%)';

                // Start receiving server-sent events for progress updates
                const eventSource = new EventSource('/upload_progress');

                eventSource.onmessage = function (event) {
                    const [message, percentage] = event.data.split(' - ');
                    progressBar.style.width = percentage;
                    progressStatus.textContent = `${message} (${percentage})`;

                    if (percentage === '100%') {
                        eventSource.close(); // Close SSE connection when complete
                    }
                };

                const response = await fetch("/", {
                    method: "POST",
                    body: formData
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const data = await response.json();

                if (data.download_url) {
                    // Hide the progress bar and status once the download link is ready
                    progressBarContainer.style.display = 'none';
                    progressStatus.style.display = 'none';

                    // Display the download button
                    downloadLink.href = data.download_url;
                    downloadButton.style.display = 'block';
                }
            } catch (error) {
                alert(`Error: ${error.message}`);
            }
        }
    });
});
