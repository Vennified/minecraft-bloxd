document.addEventListener('DOMContentLoaded', function () {
  const uploadFileBox = document.getElementById('uploadfile');
  const fileInput = document.getElementById('fileInput');
  const progressBar = document.getElementById('progress-bar');
  const progressStatus = document.getElementById('progress-status');
  const progressBarContainer = document.getElementById('progress-bar-container');
  const downloadLink = document.getElementById('downloadLink');
  const downloadSection = document.getElementById('downloadSection');

  // Trigger file input when the dashed box (#uploadfile) is clicked
  uploadFileBox.addEventListener('click', function () {
      fileInput.click();
  });

  // Handle file input change and trigger the upload
  fileInput.addEventListener('change', async function (event) {
      const file = event.target.files[0];
      if (file) {
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
                  downloadLink.href = data.download_url;
                  downloadSection.style.display = "block";
              }
          } catch (error) {
              alert(`Error: ${error.message}`);
          }
      }
  });
});
