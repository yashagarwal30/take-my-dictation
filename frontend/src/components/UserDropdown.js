import React, { useState, useRef, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaUser, FaCreditCard, FaSignOutAlt, FaChevronDown } from 'react-icons/fa';
import { UserContext } from '../context/UserContext';

const UserDropdown = () => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);
  const navigate = useNavigate();
  const { user, logout } = useContext(UserContext);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const toggleDropdown = () => {
    setIsOpen(!isOpen);
  };

  const handleNavigation = (path) => {
    setIsOpen(false);
    navigate(path);
  };

  const handleLogout = () => {
    setIsOpen(false);
    logout();
    navigate('/');
  };

  // Get user's display name or email
  const displayName = user?.full_name || user?.email || 'User';
  const firstName = displayName.split(' ')[0];

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Dropdown Button */}
      <button
        onClick={toggleDropdown}
        className="flex items-center space-x-2 px-3 py-2 rounded-lg hover:bg-gray-100 transition-colors duration-200"
      >
        <div className="flex items-center justify-center w-8 h-8 rounded-full bg-indigo-600 text-white font-semibold">
          {firstName.charAt(0).toUpperCase()}
        </div>
        <span className="hidden md:inline text-gray-700 font-medium">{firstName}</span>
        <FaChevronDown
          className={`text-gray-500 transition-transform duration-200 ${
            isOpen ? 'transform rotate-180' : ''
          }`}
        />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-50">
          {/* User Info Section */}
          <div className="px-4 py-3 border-b border-gray-200">
            <p className="text-sm font-semibold text-gray-900 truncate">{displayName}</p>
            <p className="text-xs text-gray-500 truncate">{user?.email}</p>
          </div>

          {/* Menu Items */}
          <div className="py-1">
            <button
              onClick={() => handleNavigation('/profile')}
              className="w-full flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors duration-150"
            >
              <FaUser className="mr-3 text-gray-500" />
              <span>Profile</span>
            </button>

            <button
              onClick={() => handleNavigation('/subscription/manage')}
              className="w-full flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors duration-150"
            >
              <FaCreditCard className="mr-3 text-gray-500" />
              <span>Subscription</span>
            </button>
          </div>

          {/* Logout Section */}
          <div className="border-t border-gray-200 mt-1 pt-1">
            <button
              onClick={handleLogout}
              className="w-full flex items-center px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors duration-150"
            >
              <FaSignOutAlt className="mr-3" />
              <span>Logout</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserDropdown;
