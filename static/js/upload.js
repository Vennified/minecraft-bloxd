document.addEventListener('DOMContentLoaded', function() {
  const form = document.getElementById('uploadForm');
  const fileInput = document.getElementById('file');

  form.addEventListener('submit', async (event) => {
    event.preventDefault();

    const file = fileInput.files[0];

    if (file) {
      const formData = new FormData();
      formData.append("file", file);

      try {
        const response = await fetch("/", {
          method: "POST",
          body: formData
        });

        if (!response.ok) {
          alert('Error uploading file.');
          return;
        }

        alert('File uploaded and processed successfully!');
      } catch (error) {
        console.error('Error:', error);
        alert('Error uploading file.');
      }
    } else {
      alert('No file selected.');
    }
  });
});
