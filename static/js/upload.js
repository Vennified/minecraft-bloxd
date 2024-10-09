document.addEventListener('DOMContentLoaded', function() {
  const form = document.getElementById('uploadForm');
  const fileInput = document.getElementById('file');
  const downloadSection = document.getElementById('downloadSection');
  const downloadLink = document.getElementById('downloadLink');

  form.addEventListener('submit', async (event) => {
    event.preventDefault();

    const file = fileInput.files[0];

    if (file) {
      const formData = new FormData();
      formData.append("file", file);

      try {
        // Show loading message
        alert('Uploading and processing file. Please wait...');

        const response = await fetch("/", {
          method: "POST",
          body: formData
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.error) {
          throw new Error(data.error);
        }

        if (data.download_url) {
          downloadLink.href = data.download_url;
          downloadSection.style.display = "block"; // Show download section
          alert('File uploaded and processed successfully! You can now download your processed pack.');
        } else {
          throw new Error('Download link not found in the response.');
        }
      } catch (error) {
        console.error('Error:', error);
        alert(`Error: ${error.message}`);
      }
    } else {
      alert('No file selected.');
    }
  });
});