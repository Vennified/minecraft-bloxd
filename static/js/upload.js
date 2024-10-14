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

            try {
                // Step 1: Request an upload token from your Flask backend
                const tokenResponse = await fetch('/api/generate-upload-token', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                
                if (!tokenResponse.ok) {
                    throw new Error(`Failed to get upload token! status: ${tokenResponse.status}`);
                }
                
                const { uploadUrl } = await tokenResponse.json();

                // Step 2: Upload the file to Vercel Blob
                const formData = new FormData();
                formData.append('file', file);

                const uploadResponse = await fetch(uploadUrl, {
                    method: 'POST',
                    body: formData
                });

                if (!uploadResponse.ok) {
                    throw new Error(`File upload failed! status: ${uploadResponse.status}`);
                }

                const uploadData = await uploadResponse.json();

                // Step 3: Get the uploaded file's URL and update the UI
                const fileUrl = uploadData.url;
                
                if (fileUrl) {
                    downloadLink.href = fileUrl;
                    downloadLink.style.display = 'block';
                    downloadButton.style.display = 'block';

                    uploadFilesText.textContent = 'Download Uploaded File';
                    console.log('File uploaded successfully:', fileUrl);
                } else {
                    console.error('No file URL received in the response');
                }

            } catch (error) {
                console.error('Error during upload:', error);
                alert(`Error: ${error.message}`);
            }
        }
    });
});
