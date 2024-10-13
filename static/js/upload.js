document.addEventListener('DOMContentLoaded', function () {
    const uploadFileBox = document.getElementById('uploadfile');
    const fileInput = document.getElementById('fileInput');
    const progressBar = document.getElementById('progress-bar');
    const progressStatus = document.getElementById('progress-status');
    const progressBarContainer = document.getElementById('progress-bar-container');
    const downloadLink = document.getElementById('downloadLink');
    const downloadButton = document.getElementById('downloadButton');
    const resourcePackText = document.querySelector('.resource-pack-text');
    const centerIcon = document.querySelector('.center-icon');

    uploadFileBox.addEventListener('click', function () {
        fileInput.click();
    });

    fileInput.addEventListener('change', async function (event) {
        const file = event.target.files[0];
        if (file) {
            resourcePackText.style.display = 'none';
            centerIcon.style.display = 'none';

            const formData = new FormData();
            formData.append('file', file);

            try {
                progressBarContainer.style.display = 'block';
                progressStatus.style.display = 'block';
                progressStatus.textContent = 'Uploading (0%)';

                const eventSource = new EventSource('/upload_progress');

                eventSource.onmessage = function (event) {
                    const [message, percentage] = event.data.split(' - ');
                    progressBar.style.width = percentage;
                    progressStatus.textContent = `${message} (${percentage})`;

                    if (percentage === '100%') {
                        eventSource.close();
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
                    progressBarContainer.style.display = 'none';
                    progressStatus.style.display = 'none';

                    // Update the download link href
                    downloadLink.href = data.download_url;
                    
                    // Make sure both the link and button are visible
                    downloadLink.style.display = 'block';
                    downloadButton.style.display = 'block';

                    console.log('Download URL received:', data.download_url);
                    console.log('Download link visibility:', downloadLink.style.display);
                    console.log('Download button visibility:', downloadButton.style.display);
                } else {
                    console.error('No download URL received in the response');
                }
            } catch (error) {
                console.error('Error:', error);
                alert(`Error: ${error.message}`);
            }
        }
    });
});