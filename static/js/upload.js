document.addEventListener('DOMContentLoaded', function () {
  const uploadFileBox = document.getElementById('uploadfile');
  const fileInput = document.getElementById('fileInput');
  const progressBar = document.getElementById('progress-bar');
  const progressStatus = document.getElementById('progress-status');
  const progressBarContainer = document.getElementById('progress-bar-container');
  const downloadLink = document.getElementById('downloadLink');
  const downloadSection = document.getElementById('downloadSection');
  const downloadButtonContainer = document.getElementById('downloadButtonContainer');
  const downloadButton = document.getElementById('downloadButton');

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
                      // Hide center icon and resource pack text
                      document.querySelector('.center-icon').style.display = 'none';
                      document.querySelector('.resource-pack-text').style.display = 'none';
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
                  // Show download button with background image
                  downloadButtonContainer.style.display = "block";
                  downloadButton.href = data.download_url;
                  downloadButton.style.backgroundImage = "url('path/to/your/icon.png')"; // Replace with your button icon
                  downloadButton.style.width = "200px"; // Set your desired width
                  downloadButton.style.height = "50px"; // Set your desired height
                  downloadButton.style.display = "block"; // Make it block to enable hover effect
              }
          } catch (error) {
              alert(`Error: ${error.message}`);
          }
      }
  });
});
