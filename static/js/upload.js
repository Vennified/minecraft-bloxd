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
    
                // Check if the response is JSON
                const contentType = response.headers.get("content-type");
                if (contentType && contentType.indexOf("application/json") !== -1) {
                    const data = await response.json();
                    
                    if (data.download_url) {
                        downloadLink.href = data.download_url;
                        downloadLink.style.display = 'block';
                        downloadButton.style.display = 'block';
                        uploadFilesText.textContent = 'Download Zip File';
                    } else {
                        console.error('No download URL received in the response');
                    }
                } else {
                    const errorText = await response.text();
                    throw new Error(`Unexpected response type: ${errorText}`);
                }
            } catch (error) {
                console.error('Error:', error);
                alert(`Error: ${error.message}`);
            }
        }
    });
});