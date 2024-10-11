document.addEventListener('DOMContentLoaded', function() {
  // Trigger file input when the dashed box (#uploadfile) is clicked
  document.getElementById('uploadfile').addEventListener('click', function() {
    document.getElementById('fileInput').click();
  });

  // Handle file input change and trigger the form submission
  document.getElementById('fileInput').addEventListener('change', async (event) => {
    const file = event.target.files[0]; // Get the selected file

    if (file) {
      const formData = new FormData();
      formData.append("file", file);

      try {
        alert('Uploading and processing file. Please wait...');

        // Send the form data (file) via POST request
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

          // Show the download link
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
