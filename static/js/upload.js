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
          downloadSection.style.display = "block";
          alert('File uploaded and processed successfully! You can now download your processed pack.');
          
          // Add click event listener to the download link
          downloadLink.addEventListener('click', async (e) => {
            e.preventDefault();
            try {
              const downloadResponse = await fetch(data.download_url);
              if (!downloadResponse.ok) {
                throw new Error(`Download failed: ${downloadResponse.status} ${downloadResponse.statusText}`);
              }
              const blob = await downloadResponse.blob();
              const url = window.URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.style.display = 'none';
              a.href = url;
              a.download = 'processed_pack.zip';
              document.body.appendChild(a);
              a.click();
              window.URL.revokeObjectURL(url);
            } catch (error) {
              console.error('Download error:', error);
              alert(`Error downloading file: ${error.message}`);
            }
          });
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