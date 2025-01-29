document.addEventListener('DOMContentLoaded', function () {
    // Add CSS styles
    const style = document.createElement('style');
    style.innerHTML = `
        .dropdown {
            position: relative;
            width: 600px;
        }

        @media(max-width: 650px) {
            .dropdown {
                width: 100%;
            }
        }

        .search-input {
            display: block;
            width: 100%;
            min-width: 300px;
            padding: .375rem .75rem;
            margin: 0;
            font-family: inherit;
            font-size: 1rem;
            font-weight: 400;
            line-height: 1.5;
            color: #858796;
            -webkit-appearance: none;
            -moz-appearance: none;
            appearance: none;
            background-color: #fff;
            background-clip: padding-box;
            border: 1px solid #858796;
            border-radius: 0.35rem;
            transition: border-color .15s ease-in-out, box-shadow .15s ease-in-out;
            -webkit-appearance: textfield;
            outline-offset: -2px;
        }

        .search-input:focus {
            color: #858796;
            background-color: #fff;
            border-color: #a7b9ef;
            outline: 0;
            box-shadow: 0 0 0 .15rem rgba(78, 115, 223, .25);
        }


        .dropdown-content {
            display: none;
            position: absolute;
            background-color: #f1f1f1;
            background-color: #fff;
            margin-bottom: 3rem;
            min-width: 160px;
            width: 100%;
            box-shadow: 0px 8px 16px 0px rgba(0, 0, 0, 0.2);
            z-index: 1;
            border-bottom: 1px solid #ccc;
        }

        .dropdown-content div {
            color: black;
            padding: 12px 16px;
            text-decoration: none;
            display: block;
            cursor: pointer;
        }
        .spinner {
            display: none;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #3498db;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            position: absolute;
            right: 40px;
            top: 5px;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
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

    // Create the selected section and insert it into the element with class search-result
    const searchFormContainer = document.querySelector('.search-form');
    if (searchFormContainer) {
        const dropdownDiv = document.createElement('div');
        dropdownDiv.classList.add('dropdown');

        const searchInput = document.createElement('input');
        searchInput.id = 'searchQuery';
        searchInput.classList.add('search-input');
        searchInput.setAttribute('autocomplete', 'off');
        searchInput.setAttribute('type', 'search');
        searchInput.setAttribute('name', 'q');
        searchInput.setAttribute('placeholder', 'Search Downstream Marketplace');
        searchInput.setAttribute('required', 'true');

        const spinnerDiv = document.createElement('div');
        spinnerDiv.classList.add('spinner');
        spinnerDiv.id = 'spinner';

        const dropdownContentDiv = document.createElement('div');
        dropdownContentDiv.classList.add('dropdown-content');
        dropdownContentDiv.id = 'results-container';
        dropdownContentDiv.style.zIndex = '5';

        const resultsDiv = document.createElement('div');
        resultsDiv.id = 'results';

        const paginationDiv = document.createElement('div');
        paginationDiv.id = 'pagination';
        paginationDiv.classList.add('pagination');

        dropdownContentDiv.appendChild(resultsDiv);
        dropdownContentDiv.appendChild(paginationDiv);

        dropdownDiv.appendChild(searchInput);
        dropdownDiv.appendChild(spinnerDiv);
        dropdownDiv.appendChild(dropdownContentDiv);

        searchFormContainer.appendChild(dropdownDiv);
    } else {
        console.error('Element with class search-form not found');
        return;
    }

    const searchForm = document.getElementById('searchForm');
    const searchQuery = document.getElementById('searchQuery');
    const spinner = document.getElementById('spinner');
    const resultsContainer = document.getElementById('results-container');
    const resultsDiv = document.getElementById('results');
    const paginationDiv = document.getElementById('pagination');

    let currentPage = 1;
    const resultsPerPage = 10;

    // Listen for input changes in the field and send the query to the API. Ensure at least 3 characters are entered and wait 500ms before sending the request.
    function getResults(query) {
        // Check if query is empty
        if (!query) {
            resultsContainer.style.display = 'none';
            // make searchQuery bottom border rounded again
            searchQuery.style.borderRadius = '0.35rem';
            return;
        }
        // Show spinner and disable search button
        spinner.style.display = 'block';
        // make searchQuery bottom border square
        searchQuery.style.borderRadius = '0.35rem 0.35rem 0px 0px';

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

                // Check response returns an error (query is empty)
                if (!data || data.errors) {
                    resultsContainer.style.display = 'none';
                    // make searchQuery bottom border rounded again
                    searchQuery.style.borderRadius = '0.35rem';
                    return;
                }
                // Check response is good, but has no results
                if (!data || !data.main_products || !data.main_product_categories || !data.main_product_category_groups) {
                    const listItem = document.createElement('li');
                    listItem.textContent = 'No results found';
                    resultsList.appendChild(listItem);
                    resultsDiv.appendChild(resultsList);
                    return;
                }

                const allResults = [...data.main_products, ...data.main_product_categories, ...data.main_product_category_groups];
                const totalPages = 1
                const totalResults = data.main_products.length + data.main_product_categories.length + data.main_product_category_groups.length;
                data.main_product_categories.forEach(category => {
                    const listItem = document.createElement('li');
                    const link = document.createElement('a');
                    const image = document.createElement('img');
                    const text = document.createElement('span');
                    if (category.group) {
                        text.textContent = `Category: ${category.name}`;
                        link.href = `https://portal.trydownstream.com/customer/order/new/?q=&group_id=${category.group}`;
                    } else {
                        text.textContent = `Category Group: ${category.name}`;
                        link.href = `https://portal.trydownstream.com/customer/order/new/?q=&group_id=${category.id}`;
                    }
                    image.src = category.icon;
                    // link.target = '_blank';
                    link.appendChild(image);
                    link.appendChild(text);
                    listItem.appendChild(link);
                    resultsList.appendChild(listItem);
                    const categoryProducts = data.main_products.filter(product => product.main_product_category === category.id);
                    categoryProducts.forEach(product => {
                        const listItem = document.createElement('li');
                        listItem.style.paddingLeft = '40px';
                        const link = document.createElement('a');
                        const image = document.createElement('img');
                        const text = document.createElement('span');
                        link.href = `https://portal.trydownstream.com/customer/order/new/product/${product.main_product_category}`;
                        if (product.images.length > 0) {
                            image.src = product.images[0];
                        } else {
                            image.src = category.icon;
                        }
                        text.textContent = `Product: ${product.name}`;
                        // link.target = '_blank';
                        link.appendChild(image);
                        link.appendChild(text);
                        listItem.appendChild(link);
                        resultsList.appendChild(listItem);
                    });
                });
                data.main_product_category_groups.forEach(group => {
                    const listItem = document.createElement('li');
                    const link = document.createElement('a');
                    const image = document.createElement('img');
                    const text = document.createElement('span');
                    text.textContent = `Category Group: ${group.name}`;
                    link.href = `https://portal.trydownstream.com/customer/order/new/?q=&group_id=${group.id}`;
                    image.src = group.icon;
                    // link.target = '_blank';
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
            });
    }
    let debounceTimeout
    searchQuery.addEventListener('input', function (event) {
        // Only trigger the search if the value is not empty and has more than 1 character and the user has stopped typing.
        // Clear the previous timeout
        clearTimeout(debounceTimeout)
        // Set a new timeout
        debounceTimeout = setTimeout(function () {
            if (!searchQuery.value || searchQuery.value.length > 2) {
                const query = searchQuery.value;
                console.log('query', query);
                // event.preventDefault();
                getResults(query);
            }
        }, 500)
    });
});