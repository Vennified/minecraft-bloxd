document.addEventListener('DOMContentLoaded', function () {
    const uploadFileBox = document.getElementById('uploadfile');
    const fileInput = document.getElementById('fileInput');
    const downloadLink = document.getElementById('downloadLink');
    const downloadButton = document.getElementById('downloadButton');
    const resourcePackText = document.querySelector('.resource-pack-text');
    const centerIcon = document.querySelector('.center-icon');
    const uploadFilesText = document.querySelector('.upload-files-text');

    uploadFileBox.addEventListener('click', function () {
        fileInput.click();
    });

    fileInput.addEventListener('change', async function (event) {
        const file = event.target.files[0];
        if (file) {
            resourcePackText.style.display = 'none';
            centerIcon.style.display = 'none';
            downloadLink.style.display = 'none';
            downloadButton.style.display = 'none';

            uploadFilesText.textContent = 'Uploading...';

            const formData = new FormData();
            formData.append('file', file);

            try {
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
                    
                    downloadLink.style.display = 'block';
                    downloadButton.style.display = 'block';

                    uploadFilesText.textContent = 'Download Zip File';

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