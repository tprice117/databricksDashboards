document.addEventListener('DOMContentLoaded', function () {
    // Add CSS styles
    const style = document.createElement('style');
    style.innerHTML = `
        .spinner {
            display: none;
            width: 50px;
            height: 50px;
            border: 5px solid #f3f3f3;
            border-top: 5px solid #3498db;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .dropdown-content {
            display: none;
            position: absolute;
            position: relative;
            width: 100%;
            max-width: 600px;
            background-color: #f9f9f9;
            background-color: #fff;
            min-width: 160px;
            box-shadow: 0px 8px 16px 0px rgba(0,0,0,0.2);
            z-index: 1000;
            border-bottom: 1px solid #ccc;
        }

        .results-list {
            list-style-type: none;
            padding: 0;
            margin: 0;
            max-height: 400px;
            overflow-y: auto;
            border: 1px solid #ccc;
            border-radius: 4px;
            background-color: #fff;
            position: relative;
            width: 100%;
            
        }
        .results-list li {
            padding: 10px;
            cursor: pointer;
            display: flex;
            align-items: center;
            border-bottom: 1px solid #ccc;
        }

        .results-list li img {
            width: 50px;
            height: 50px;
            margin-right: 10px;
        }

        .results-list li:hover {
            background-color: #f0f0f0;
        }

        .pagination {
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 10px;
        }

        .pagination button {
            margin: 0 5px;
            padding: 5px 10px;
            cursor: pointer;
        }

        .pagination button:disabled {
            cursor: not-allowed;
            opacity: 0.5;
        }

        .results-count {
        }
    `;
    document.head.appendChild(style);

    const searchForm = document.getElementById('searchForm');
    const searchQuery = document.getElementById('searchQuery');
    const searchButton = document.getElementById('searchButton');
    const spinner = document.getElementById('spinner');
    const resultsContainer = document.getElementById('results-container');
    const resultsDiv = document.getElementById('results');
    const paginationDiv = document.getElementById('pagination');

    let currentPage = 1;
    const resultsPerPage = 10;

    searchForm.addEventListener('submit', function (event) {
        event.preventDefault();
        const query = searchQuery.value;

        // Show spinner and disable search button
        spinner.style.display = 'block';
        searchButton.disabled = true;

        fetch(`https://api.trydownstream.com/explore/v1/search/?q=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => {
                // Clear previous results
                resultsDiv.innerHTML = '';
                paginationDiv.innerHTML = '';
                resultsContainer.style.display = 'block';

                // Display search results
                const resultsList = document.createElement('ul');
                resultsList.classList.add('results-list');

                const allResults = [...data.main_products, ...data.main_product_categories];
                const totalPages = 1
                const totalResults = allResults.length;
                allResults.forEach(result => {
                    const listItem = document.createElement('li');
                    const link = document.createElement('a');
                    const image = document.createElement('img');
                    const text = document.createElement('span');

                    if (result.images) {
                        // https://portal.trydownstream.com/customer/order/new/product/5edb42d6-929c-4d79-ab8f-ea8f7624400c/
                        link.href = `https://portal.trydownstream.com/customer/order/new/product/${result.main_product_category}`;
                        image.src = result.images[0];
                        text.textContent = `Product: ${result.name}`;
                    } else {
                        // https://portal.trydownstream.com/customer/order/new/?q=&group_id=e14ef474-eacf-4e13-8f15-b67bb9f68413
                        link.href = `https://portal.trydownstream.com/customer/order/new/?q=&group_id=${result.group}`;
                        image.src = result.icon;
                        text.textContent = `Category: ${result.name}`;
                    }
                    link.target = '_blank';
                    link.appendChild(image);
                    link.appendChild(text);
                    listItem.appendChild(link);
                    resultsList.appendChild(listItem);
                });
                resultsDiv.appendChild(resultsList);

                // Clear previous pagination
                paginationDiv.innerHTML = '';
                const resultsCount = document.createElement('span');
                resultsCount.classList.add('results-count');
                resultsCount.textContent = `Showing ${totalResults} results`;
                paginationDiv.appendChild(resultsCount);
            })
            .catch(error => console.error('Error:', error))
            .finally(() => {
                // Hide spinner and enable search button
                spinner.style.display = 'none';
                searchButton.disabled = false;
            });
    });
});