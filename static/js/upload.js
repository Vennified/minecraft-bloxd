document.addEventListener('DOMContentLoaded', function() {
  const dashedBox = document.querySelector('.dashed-box');
  const fileInput = document.getElementById('file');

  // Trigger file input when dashed-box is clicked
  dashedBox.addEventListener('click', function() {
    fileInput.click();
  });

  // Handle file input change and trigger the form submission
  fileInput.addEventListener('change', async (event) => {
    const file = fileInput.files[0];

    if (file) {
      const formData = new FormData();
      formData.append("file", file);

      try {
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
          const downloadLink = document.getElementById('downloadLink');
          const downloadSection = document.getElementById('downloadSection');

          downloadLink.href = data.download_url;
          downloadSection.style.display = "block";
          alert('File uploaded and processed successfully! You can now download your processed pack.');
        }
      } catch (error) {
        alert(`Error: ${error.message}`);
      }
    }
  });
});
