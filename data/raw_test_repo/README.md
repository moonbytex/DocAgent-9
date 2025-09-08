# Vending Machine Test Repository

A comprehensive vending machine implementation in Python that demonstrates various programming concepts, design patterns, and documentation styles. This repository serves as a test bed for docstring generation systems and code documentation analysis.

## Project Structure

```
test_repo_vm/
├── __init__.py              # Main package initialization
├── example.py              # Example usage demonstration
├── vending_machine.py      # Main vending machine implementation
├── models/                 # Data models
│   ├── __init__.py
│   └── product.py         # Product class definition
├── payment/               # Payment processing
│   ├── __init__.py
│   └── payment_processor.py # Payment-related classes
└── inventory/            # Inventory management
    ├── __init__.py
    └── inventory_manager.py # Inventory tracking system
```

## Components

### 1. Product Management (`models/product.py`)
- `Product` class with attributes like ID, name, price, quantity, and expiry date
- Methods for checking availability and managing stock

### 2. Payment Processing (`payment/payment_processor.py`)
- Abstract `PaymentMethod` base class for different payment types
- `CashPayment` implementation for handling cash transactions
- `PaymentTransaction` class for tracking payment status
- `PaymentStatus` enum for transaction states

### 3. Inventory Management (`inventory/inventory_manager.py`)
- `InventoryManager` class for product storage and retrieval
- Slot-based product organization
- Stock level tracking
- Product availability checking

### 4. Main Vending Machine (`vending_machine.py`)
- `VendingMachine` class that coordinates all components
- Product selection and purchase workflow
- Payment processing and change calculation
- Exception handling for error cases

## Code Features

This repository demonstrates various Python programming features:

1. **Object-Oriented Design**
   - Abstract base classes
   - Inheritance
   - Encapsulation
   - Interface definitions

2. **Modern Python Features**
   - Type hints
   - Dataclasses
   - Enums
   - Optional types
   - Package organization

3. **Documentation**
   - Comprehensive docstrings
   - Type annotations
   - Code organization
   - Exception documentation

4. **Best Practices**
   - SOLID principles
   - Clean code architecture
   - Error handling
   - Modular design

## Usage Example

```python
from decimal import Decimal
from vending_machine import VendingMachine
from models.product import Product

# Create a vending machine
vm = VendingMachine()

# Add products
product = Product(
    id="COLA001",
    name="Cola Classic",
    price=1.50,
    quantity=10,
    category="drinks"
)
vm.inventory.add_product(product, slot=0)

# Insert money
vm.insert_money(Decimal('2.00'))

# Purchase product
product, change = vm.purchase_product(slot=0)
print(f"Purchased: {product.name}")
print(f"Change: ${change:.2f}")
```

## Running the Example

To run the example implementation:

```bash
python example.py
```

This will demonstrate:
1. Creating a vending machine
2. Adding products to inventory
3. Displaying available products
4. Making a purchase
5. Handling change
6. Updating inventory

## Testing Documentation Generation

This repository is structured to test various aspects of documentation generation:

1. **Complex Imports**
   - Cross-module dependencies
   - Package-level imports
   - Relative imports

2. **Documentation Styles**
   - Function documentation
   - Class documentation
   - Module documentation
   - Package documentation

3. **Code Complexity**
   - Multiple inheritance
   - Abstract classes
   - Type annotations
   - Exception hierarchies

## Requirements

- Python 3.7+
- No external dependencies required

## License

This project is open source and available under the MIT License. 