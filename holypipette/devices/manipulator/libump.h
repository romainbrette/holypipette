/**
 * @file    libump.h
 * @author  Sensapex <support@sensapex.com>
 * @date    29 November 2017
 * @brief   This file contains a public API for the 2015 series Sensapex Micromanipulator SDK
 * @copyright   Copyright (c) 2016 Sensapex. All rights reserved
 *
 * The Sensapex micromanipulator SDK is free software: you can redistribute
 * it and/or modify it under the terms of the GNU Lesser General Public License
 * as published by the Free Software Foundation, either version 3 of the License,
 * or (at your option) any later version.
 *
 * The Sensapex Micromanipulator SDK is distributed in the hope that it will be
 * useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with the Sensapex micromanipulator SDK. If not, see
 * <http://www.gnu.org/licenses/>.
 */

#ifndef LIBUMP_H
#define LIBUMP_H

#if defined(WIN32) || defined(WIN64) || defined(_WIN32) || defined(_WIN64)
# ifndef _WINDOWS
#  define _WINDOWS
# endif
#ifdef _WINDOWS
#  include <winsock2.h>
#  include <ws2tcpip.h>
#  include <stdint.h>  // for uint32_t
#  define SOCKOPT_CAST (char *)             /**< cross platform trick, non-standard variable type requires typecasting in windows for socket options */
#  define socklen_t int                     /**< cross platform trick, socklen_t is not defined in windows */
#  define getLastError()  WSAGetLastError() /**< cross platform trick, using winsocket function instead of errno */
#  define timeoutError    WSAETIMEDOUT      /**< cross platform trick, detect timeout with winsocket error number */
typedef struct sockaddr_in IPADDR;          /**< alias for sockaddr_in */
# endif
// Define this is embedding SDK into application directly, but note the LGPL license requirements
# ifdef  LIBUMP_SHARED_DO_NOT_EXPORT
#  define LIBUMP_SHARED_EXPORT
# else
#  if defined(LIBUMP_LIBRARY)
#   define LIBUMP_SHARED_EXPORT __declspec(dllexport) /**< cross platform trick, declspec for windows*/
#  else
#   define LIBUMP_SHARED_EXPORT __declspec(dllimport) /**< cross platform trick, declspec for windows*/
#  endif
# endif
#else
# define LIBUMP_SHARED_EXPORT               /**< cross platform trick, declspec for windows DLL, empty for posix systems */
# include <unistd.h>
# include <arpa/inet.h>
# include <sys/errno.h>
typedef int SOCKET;                         /**< cross platform trick, int instead of SOCKET (defined by winsock) in posix systems */
typedef struct sockaddr_in IPADDR;          /**< alias for sockaddr_in */
# define SOCKET_ERROR   -1                  /**< cross platform trick, replace winsocket return value in posix systems */
# define INVALID_SOCKET -1                  /**< cross platform trick, replace winsocket return value in posix systems */
# define getLastError() errno               /**< cross platform trick, errno instead of WSAGetLastError() in posix systems */
# define timeoutError   ETIMEDOUT           /**< cross platform trick, errno ETIMEDOUT instead of WSAETIMEDOUT in posix systems */
# define closesocket    close               /**< cross platform trick, close() instead of closesocket() in posix systems */
# define SOCKOPT_CAST                       /**< cross platform trick, non-standard typecast not needed in posix systems */
#endif

#ifdef _WINDOWS
# include <windows.h>
#ifndef LIBUMP_SHARED_DO_NOT_EXPORT
LIBUMP_SHARED_EXPORT HRESULT __stdcall DllRegisterServer(void);
LIBUMP_SHARED_EXPORT HRESULT __stdcall DllUnregisterServer(void);
#endif
#endif

/*
 * The precompiler condition below is utilized by C++ compilers and is
 * ignored by pure C ones
 */
#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief SDK error enums
 */
typedef enum ump_error_e
{
    LIBUMP_NO_ERROR     =  0,  /**< No error */
    LIBUMP_OS_ERROR     = -1,  /**< Operating System level error */
    LIBUMP_NOT_OPEN     = -2,  /**< Communication socket not open */
    LIBUMP_TIMEOUT      = -3,  /**< Timeout occured */
    LIBUMP_INVALID_ARG  = -4,  /**< Illegal command argument */
    LIBUMP_INVALID_DEV  = -5,  /**< Illegal Device Id */
    LIBUMP_INVALID_RESP = -6,  /**< Illegal response received */
} ump_error;

/**
 * @brief Manipulator status enums
 *
 * These cause busy state
 */
typedef enum ump_status_e
{
    LIBUMP_STATUS_READ_ERROR = -1,     /**< Failure at status reading */
    LIBUMP_STATUS_OK         = 0,      /**< No error and status idle */
    LIBUMP_STATUS_BUSY       = 1,      /**< Manipulator busy (not necessarily moving) */
    LIBUMP_STATUS_ERROR      = 8,      /**< Manipulator in error state */
    LIBUMP_STATUS_X_MOVING   = 0x10,   /**< X-actuator is busy */
    LIBUMP_STATUS_Y_MOVING   = 0x20,   /**< Y-actuator is busy */
    LIBUMP_STATUS_Z_MOVING   = 0x40,   /**< Z-actuator is busy */
    LIBUMP_STATUS_W_MOVING   = 0x80,   /**< 4th actuator is busy */

    LIBUMP_STATUS_JAMMED     = 0x80    /**< A manipulator is stucked */
} ump_status;

/*
 * Some default values and other platform independent defines
 */

#define LIBUMP_DEF_STORAGE_ID      0        /**< default position storage */
#define LIBUMP_DEF_TIMEOUT         20       /**< default message timeout in millisecods */
#define LIBUMP_DEF_BCAST_ADDRESS  "169.254.255.255" /**< default link-local broadcast address */
#define LIBUMP_DEF_GROUP           0        /**< default manipulator group, group 0 is called 'A' on TCU UI */
#define LIBUMP_MAX_TIMEOUT         1000     /**< maximum message timeout in milliseconds */
#define LIBUMP_MAX_LOG_LINE_LENGTH 256      /**< maximum log message length */

#define LIBUMP_ARG_UNDEF    INT32_MAX       /**< function argument undefined (used when 0 is a valid value */
#define LIBUMP_FEATURE_VIRTUALX    0        /**< id number for virtual X axis feature */


#define LIBUMP_MAX_MANIPULATORS   254       /**< Max count of concurrent manipulators supported by this SDK version*/
#define LIBUMP_DEF_REFRESH_TIME    20       /**< The default positions refresh period in ms */
#define LIBUMP_MAX_POSITION     20400       /**< The upper absolute position limit for actuators */

#define LIBUMP_TIMELIMIT_CACHE_ONLY 0       /**< Read position always from the cache */
#define LIBUMP_TIMELIMIT_DISABLED  -1       /**< Skip the internal position cache.
                                                 Use this definition as a parameter to read an actuator position
                                                 directly from a manipulator */

#define LIBUMP_TSC_SPEED_MODE_SNAIL 1       /**< TSC speed mode for snail mode */
#define LIBUMP_TSC_SPEED_MODE_1     2       /**< TSC speed mode for speed 1 */
#define LIBUMP_TSC_SPEED_MODE_2     3       /**< TSC speed mode for speed 2 */
#define LIBUMP_TSC_SPEED_MODE_3     4       /**< TSC speed mode for speed 3 */
#define LIBUMP_TSC_SPEED_MODE_4     5       /**< TSC speed mode for speed 4 */
#define LIBUMP_TSC_SPEED_MODE_5     6       /**< TSC speed mode for speed 5 */
#define LIBUMP_TSC_SPEED_MODE_PEN   7       /**< TSC speed mode for penetration */

#define LIBUMP_POS_DRIVE_COMPLETED  0       /**< (memory) position drive completed */
#define LIBUMP_POS_DRIVE_BUSY       1       /**< (memory) position drive busy */
#define LIBUMP_POS_DRIVE_FAILED    -1       /**< (memory) position drive failed */

/**
 * @brief Positions used in #ump_state
 */
typedef struct ump_positions_s
{
    int x;                 /**< X-actuator position */
    int y;                 /**< Y-actuator position */
    int z;                 /**< Z-actuator position */
    int w;                 /**< W-actuator position */
    float speed_x;         /**< X-actuator movement speed between last two position updates */
    float speed_y;         /**< Y-actuator movement speed between last two position updates */
    float speed_z;         /**< Z-actuator movement speed between last two position updates */
    float speed_w;         /**< W-actuator movement speed between last two position updates */
    unsigned long long updated_us; /**< Timestamp (in microseconds) when positions were updated */
} ump_positions;

/**
 * @brief Prototype for the log print callback function
 *
 * @param   level   Verbosity level of the message
 * @param   arg     Optional argument e.g. a file handle, optional, may be NULL
 * @param   message Pointer to a static buffer containing the log print line without trailing line feed
 *
 * @return  Pointer to an error string
 */

typedef void (*ump_log_print_func)(int level, const void *arg, const char *func, const char *message);

/**
 * @brief The state struct, pointer to this is the session handle in the C API
 */
typedef struct ump_state_s
{
    unsigned long last_received_time;                   /**< Timestemp of the latest incoming message */
    SOCKET socket;                                      /**< UDP socket */
    int own_id;                                         /**< The device ID if this SDK */
    unsigned short message_id;                          /**< Message id (autoincremented counter for messages sent by this SDK */
    int last_device_sent;                               /**< Device ID of selected and/or communicated target device */
    int last_device_received;                           /**< ID of device that has sent the latest message */
    int retransmit_count;                               /**< Resend count for requests requesting ACK */
    int refresh_time_limit;                             /**< Refresh time limit for the position cache */
    int last_error;                                     /**< Error code of the latest error */
    int last_os_errno;                                  /**< OS level errno of the latest error */
    int timeout;                                        /**< UDP transport message timeout */
    int udp_port;                                       /**< Target UDP port */
    int last_status[LIBUMP_MAX_MANIPULATORS];           /**< Manipulator status cache */
    int drive_status[LIBUMP_MAX_MANIPULATORS];          /**< Manipulator (memory) position drive state #LIBUMP_DRIVE_BUSY, #LIBUMP_DRIVE_COMPLETED or #LIBUMP_DRIVE_FAILED */
    unsigned short drive_status_id[LIBUMP_MAX_MANIPULATORS]; /**< message ids of the above notifications, used to detect duplicates */
    IPADDR addresses[LIBUMP_MAX_MANIPULATORS];         /**< manipulator address cache */
    IPADDR cu_address;                                  /**< Touch Control Unit (TCU) address */
    ump_positions last_positions[LIBUMP_MAX_MANIPULATORS];   /**< Position cache */
    IPADDR laddr;                                       /**< UDP local address */
    IPADDR raddr;                                       /**< UDP remote address */
    char errorstr_buffer[LIBUMP_MAX_LOG_LINE_LENGTH];   /**< The work buffer of the latest error string handler */
    int verbose;                                        /**< Enable log printouts to stderr, utilized for SDK development */
    ump_log_print_func log_func_ptr;                    /**< External log print function pointer */
    const void *log_print_arg;                          /**< Argument for the above */
    int next_cmd_options;                               /**< Option bits to set for the smcp commands */
} ump_state;

/**
 * @brief Open UDP socket, allocate and initialize state structure
 *
 * @param   udp_target_address    typically an UDP broadcast address
 * @param   timeout               message timeout in milliseconds
 * @param   group                 manipulator group, 0 for default group 'A' on TCU UI
 *
 * @return  Pointer to created session handle. NULL if an error occured
 */

LIBUMP_SHARED_EXPORT ump_state *ump_open(const char *udp_target_address, const unsigned int timeout, const int group);

/**
 * @brief Close the UDP socket if open and free the state structure allocated in open
 *
 * @param   hndl    Pointer to session handle
 * @return  None
 */

LIBUMP_SHARED_EXPORT void ump_close(ump_state *hndl);


/**
 * For most C functions returning int, a negative values means error,
 * got the possible error number or description using some of these functions
 * often the last one is enough.
 */

/**
 * @brief Get the latest error
 *
 * @param   hndl    Pointer to session handle
 * @return  `ump_error` error code
 */
LIBUMP_SHARED_EXPORT ump_error ump_last_error(const ump_state *hndl);

/**
 * @brief This function can be used to get the actual operating system level error number
 * when ump_last_error returns LIBUMP_OS_ERROR.
 *
 * @param   hndl    Pointer to session handle
 * @return  Error code
 */
LIBUMP_SHARED_EXPORT int ump_last_os_errno(const ump_state *hndl);

/**
 * @brief Translate an error code to human readable format
 *
 * @param   error_code    Error code to be translated to text string
 * @return  Pointer to an error string
 */
LIBUMP_SHARED_EXPORT const char *ump_errorstr(const ump_error error_code);

/**
 * @brief Get the latest error in human readable format
 *
 * @param   hndl    Pointer to session handle
 * @return  Pointer to an error string
 */
LIBUMP_SHARED_EXPORT const char *ump_last_errorstr(ump_state *hndl);


/**
 * @brief Set up external log print functio by default the library writes
 *        to the stderr if verbose level is higher than zero.
 *
 * @param   hndl            Pointer to session handle
 * @param   verbose_level   Verbose level (zero to disable, higher value for more detailed printouts)
 * @param   func            Pointer to the custom log print function.
 *                          May be NULL if setting only verbose level for internal log print out to stderr
 * @param   arg             Pointer argument to be looped to the above function may be e.g. a typecasted
 *                          file handle, optional, may be NULL
 * @return  Negative value if an error occured. Zero or positive value otherwise
 */

LIBUMP_SHARED_EXPORT int ump_set_log_func(ump_state *hndl, const int verbose_level,
                                          ump_log_print_func func, const void *arg);

/**
 * @brief SDK library version
 *
 * @return  Pointer to version string
 */
LIBUMP_SHARED_EXPORT const char *ump_get_version();

/**
 * @brief Get the manipulator firmware version
 *
 * @param       hndl    Pointer to session handle
 * @param[out]  version Pointer to an allocated buffer for firmware numbers
 * @param       size    size of the above buffer (number of integers)
 *
 * This function should be called in this way
 * int version_buffer[4];
 * int ret = ump_read_version(handle, buffer, 4);
 *
 * @return  Negative value if an error occured. Zero or positive value otherwise
 */

LIBUMP_SHARED_EXPORT int ump_read_version(ump_state * hndl, int *version, const int size);

/**
 * @brief Get the manipulator axis count
 *
 * @param       hndl    Pointer to session handle
 * @return  Negative value if an error occured. Axis count otherwise
 */

LIBUMP_SHARED_EXPORT int ump_get_axis_count(ump_state * hndl, const int dev);


/*
 * The simplified interface stores both the device, speed mode and refresh time
 * into the state structure and utilize those for all request
 */

/**
 * @brief Select a manipulator
 *
 * @param   hndl    Pointer to session handle
 * @param   dev     Device ID of manipulator
 * @return  Negative value if an error occured. Zero or positive value otherwise
 */

LIBUMP_SHARED_EXPORT int ump_select_dev(ump_state *hndl, const int dev);

/**
 * @brief Set refresh timelimit for the session position cache
 *
 * @param   hndl    Pointer to session handle
 * @param   value   New refresh timelimit for position cache (in milliseconds).
 * @return  Negative value if an error occured. Zero or positive value otherwise
 */

LIBUMP_SHARED_EXPORT int ump_set_refresh_time_limit(ump_state *hndl,
                                                    const int value);
/**
 * @brief Change request timeout
 *
 * Initial value os set when socket opened
 *
 * @param   hndl    Pointer to session handle
 * @param   value   New serial port timeout (in milliseconds)
 * @return  Negative value if an error occured. Zero or positive value otherwise
 */

LIBUMP_SHARED_EXPORT int ump_set_timeout(ump_state *hndl, const int value);

/**
 * @brief Read the manipulator status
 *
 * @param   hndl    Pointer to session handle
 * @return  Status of the selected manipulator. See #ump_status for bit definitions
 */

LIBUMP_SHARED_EXPORT ump_status ump_get_status(ump_state *hndl);

/*
 * Status is a bit map and not all bits mean the manipulator being busy.
 * Detect busy state using these functions
 */
/**
 * @brief Check if the manipulator is busy
 *
 * @param   hndl    Pointer to session handle
 * @return  Positive value if the target manipulator is busy.
 *          Zero if the target manipulator is not busy. Negative value indicates an error
 */

LIBUMP_SHARED_EXPORT int ump_is_busy(ump_state *hndl);

/**
 * @brief Check a busy status
 *
 * @param   status   `ump_status` value to be checked
 * @return  Positive value if 'status' is a busy status.
 *          Zero if 'status' is not a busy status. Negative value indicates an error
 */

LIBUMP_SHARED_EXPORT int ump_is_busy_status(const ump_status status);

/**
 * @brief Obtain selected manipulator memory or position drive status
 *
 * @param   hndl    Pointer to session handle
 * @return  Status of the selected manipulator, #LIBUMP_POS_DRIVE_COMPLETED,
 *          #LIBUMP_POS_DRIVE_BUSY or #LIBUMP_POS_DRIVE_FAILED
 */

LIBUMP_SHARED_EXPORT int ump_get_drive_status(ump_state *hndl);

/**
 * @brief Take a step (relative movement from current position)
 *
 * @param   hndl    Pointer to session handle
 * @param   x,y,z,w step length (in nm), negative value for backward, zero for axis not to be moved
 * @param   speed
 * @return  Zero or positive value if the operation was successful. Negative value indicates an error
 */

LIBUMP_SHARED_EXPORT int ump_take_step(ump_state * hndl, const int x, const int y, const int z, const int w, const int speed);

/**
 * @brief ump_cmd_get_axis_angle
 * @param hndl  Pointer to session handle
 * @param dev Device id
 * @param axis  x=0,y=1,z=2,w=3
 * @param layer x-layer = 0, y-layer = 1, z-layer = 2
 * @return Integer value of asked axis angle
 */
LIBUMP_SHARED_EXPORT int ump_cmd_get_axis_angle(ump_state * hndl, const int dev, const int axis, const int layer);


/**
 * @brief ump_take_jackhammer_step (moving manipulator with PEN mode max speed steps with 2 pulses
 *
 * @param hndl                  Pointer to session handle
 * @param axis                  Target actuator: X == 0, Y == 1, Z == 2, W == 3
 * @param iterations            Amount of iterations (loops) to execute 2 pulse sequence
 * @param pulse1_step_count     First pulse step count
 * @param pulse1_step_size      First pules step burst size - negative indicates backward movement
 * @param pulse2_step_count     Second pules step count
 * @param pulse2_step_size      Second uples step burst size - negative indicates backward movement
 * @return
 */
LIBUMP_SHARED_EXPORT int ump_take_jackhammer_step(ump_state *hndl,
                                                  const int axis,
                                                  const int iterations,
                                                  const int pulse1_step_count, const int pulse1_step_size,
                                                  int pulse2_step_count, const int pulse2_step_size);


/**
 * @brief Obtain the actuator position
 *
 * @param   hndl    Pointer to session handle
 * @param[out]   x  Pointer to x-actuator position. (may be NULL)
 * @param[out]   y  Pointer to y-actuator position. (may be NULL)
 * @param[out]   z  Pointer to z-actuator position. (may be NULL)
 * @param[out]   w  Pointer to w-actuator position. (may be NULL)
 * @return  The number of stored values.
 *          Negative value indicates an error
 */

LIBUMP_SHARED_EXPORT int ump_get_positions(ump_state *hndl, int *x, int *y, int *z, int *w);

/**
 * @brief Obtain the actuator speeds
 *
 * @param   hndl    Pointer to session handle
 * @param[out]   x  Pointer to x-actuator speed. (may be NULL)
 * @param[out]   y  Pointer to y-actuator speed. (may be NULL)
 * @param[out]   z  Pointer to z-actuator speed. (may be NULL)
 * @param[out]   w  Pointer to w-actuator speed. (may be NULL)
 * @return  The number of stored values.
 *          Negative value indicates an error
 */

LIBUMP_SHARED_EXPORT int ump_get_speeds(ump_state *hndl, float *x, float *y, float *z, float *w);

/**
 * @brief Read positions from the manipulator to the cache, use e.g. #ump_get_x_position
 * to obtain position value without the need to use pointer
 *
 * @param       hndl        Pointer to session handle
 * @return  axis position
 */

LIBUMP_SHARED_EXPORT int ump_read_positions(ump_state *hndl);

/**
 * @brief Obtain X axis position from the cache, call after successfull #ump_read_positions
 *
 *
 * @param       hndl        Pointer to session handle
 * @return  axis position
 */

LIBUMP_SHARED_EXPORT int ump_get_x_position(ump_state *hndl);

/**
 * @brief Obtain Y axis position from the cache, call after successfull #ump_read_positions
 *
 *
 * @param       hndl        Pointer to session handle
 * @return  axis position
 */

LIBUMP_SHARED_EXPORT int ump_get_y_position(ump_state *hndl);

/**
 * @brief Obtain Z axis position from the cache, call after successfull #ump_read_positions
 *
 *
 * @param       hndl        Pointer to session handle
 * @return  axis position
 */

LIBUMP_SHARED_EXPORT int ump_get_z_position(ump_state *hndl);

/**
 * @brief Obtain W (4th) axis position from the cache, call after successfull #ump_read_positions
 *
 *
 * @param       hndl        Pointer to session handle
 * @return  axis position
 */

LIBUMP_SHARED_EXPORT int ump_get_w_position(ump_state *hndl);

/**
 * @brief Store the current position into memory location.
 *
 * @param   hndl    Session handle
 * @return  Negative value if an error occured. Zero or positive value otherwise
 */

LIBUMP_SHARED_EXPORT int ump_store_mem_current_position(ump_state *hndl);

/**
 * @brief Goto to a defined position
 *
 * @param   hndl        Pointer to session handle
 * @param   x, y, z, w  Target position, #LIBUMP_ARG_UNDEF for axis not to be moved.
 * @param   speed       movement speed in um/s
 * @return  Negative value if an error occured. Zero or positive value otherwise
 */

LIBUMP_SHARED_EXPORT int ump_goto_position(ump_state *hndl, const int x, const int y, const int z, const int w, const int speed);

/**
 * @brief Goto to a virtual axis position
 *
 * @param   hndl        Pointer to session handle
 * @param   x_position  Target virtual axis X position (nm).
 * @param   speed       movement speed in um/s
 * @return  Negative value if an error occured. Zero or positive value otherwise
 */

LIBUMP_SHARED_EXPORT int ump_goto_virtual_axis_position(ump_state *hndl, const int x_position, const int speed);


/**
 * @brief Drive selected manipulator to a stored position
 *
 * @param   hndl    Pointer to session handle
 * @param   speed   Movement speed in um/s
 * @param   storage_id  The destination memory location.
 *                      (1 = home, 2 = target, ...)
 * @return  Negative value if an error occured. Zero or positive value otherwise
 */

LIBUMP_SHARED_EXPORT int ump_goto_mem_position(ump_state *hndl, const int speed, const int storage_id);

/**
 * @brief  Stop selected manipulator movement.
 *
 * @param       hndl    Pointer to session handle
 * @return  Negative value if an error occured. Zero or positive value otherwise
 */

LIBUMP_SHARED_EXPORT int ump_stop(ump_state *hndl);

/**
 * @brief  Stop all moving manipulators.
 *
 * @param       hndl    Pointer to session handle
 * @return  Negative value if an error occured. Zero or positive value otherwise
 */

LIBUMP_SHARED_EXPORT int ump_stop_all(ump_state *hndl);

/**
 * Lower layer API carrying the device id and extended arguments.
 * These functions are used internally by the above API functions.
 * They are typically more convenient than the simplified version if
 * the application needs to control multiple manipulators at the same time
 */

/**
 * @brief Ping a manipulator
 *
 * @param   hndl    Pointer to session handle
 * @param   dev     Device ID
 * @return  Negative value if an error occured. Zero or positive value otherwise
 */
LIBUMP_SHARED_EXPORT int ump_ping(ump_state *hndl, const int dev);

/**
 * @brief Lower layer API to check if a certain manipulator is busy.
 *
 * @param   hndl    Pointer to session handle
 * @param   dev     Device ID
 * @return  Negative value if an error occured. Zero or positive value otherwise
 */

LIBUMP_SHARED_EXPORT int ump_is_busy_ext(ump_state *hndl, const int dev);

/**
 * @brief Lower layer API to obtain a status of a certain manipulator.
 *
 * @param   hndl    Pointer to session handle
 * @param   dev     Device ID
 * @return  status see #ump_status for bit definitis,
 * when typecasted to int, negative value indicates an error.
 *
 */

LIBUMP_SHARED_EXPORT ump_status ump_get_status_ext(ump_state *hndl, const int dev);

/**
 * @brief Obtain memory or position drive status of certain manipulator
 *
 * @param   hndl    Pointer to session handle
 * @param   dev     Device ID
 *
 * @return  Status of the selected manipulator, #LIBUMP_POS_DRIVE_COMPLETED,
 *          #LIBUMP_POS_DRIVE_BUSY or #LIBUMP_POS_DRIVE_FAILED
 */

LIBUMP_SHARED_EXPORT int ump_get_drive_status_ext(ump_state *hndl, const int dev);

/**
 * @brief Lower layer API to read manipulator firmware version.
 *
 * @param   hndl    Pointer to session handle
 * @param   dev     Device ID
 * @param[out]  version   Pointer to an allocated buffer for firmware numbers
 * @param   size    size of the above buffer (number of integers)
 * @return  Negative value if an error occured. Zero or positive value otherwise
 */

LIBUMP_SHARED_EXPORT int ump_read_version_ext(ump_state *hndl, const int dev,
                                              int *version, const int size);


/**
 * @brief Lower layer API to read manipulator axis count
 *
 * @param   hndl    Pointer to session handle
 * @param   dev     Device ID
 * @return  Negative value if an error occured. Axis count otherwise
 */

LIBUMP_SHARED_EXPORT int ump_get_axis_count_ext(ump_state * hndl, const int dev);

/**
 * @brief An advanced API to store current position.
 *
 * @param   hndl        Pointer to session handle
 * @param   dev         Device ID
 * @param   storage_id  The destination memory location.
 *                      (0 = default, 1 = home, 2 = target, ...)
 * @return  Negative value if an error occured. Zero or positive value otherwise
 */

LIBUMP_SHARED_EXPORT int ump_store_mem_current_position_ext(ump_state *hndl, const int dev, const int storage_id);

/**
 * @brief An advanced API to drive certain manipulator to a defined position.
 *
 * @param   hndl        Pointer to session handle
 * @param   dev         Device ID
 * @param   x, y, z, w  Positions, LIBUMP_ARG_UNDEF for axis not to be moved
 * @param   speed       speed in um/s
 * @param   mode        0 = one-by-one, 1 = move all axis simultanously.
 * @return  Negative value if an error occured. Zero or positive value otherwise
 */

LIBUMP_SHARED_EXPORT int ump_goto_position_ext(ump_state *hndl, const int dev,
                                               const int x, const int y,
                                               const int z, const int w,
                                               const int speed, const int mode);


/**
 * @brief An advanced API to goto to a virtual axis position
 *
 * @param   hndl        Pointer to session handle
 * @param   dev         Device ID
 * @param   x_position  Target virtual axis X position (nm).
 * @param   speed       movement speed in um/s
 * @return  Negative value if an error occured. Zero or positive value otherwise
 */

LIBUMP_SHARED_EXPORT int ump_goto_virtual_axis_position_ext(ump_state *hndl, const int dev,
                                                        const int x_position, const int speed);
/**
 * @brief An advanced API to move actuators to a stored position.
 *
 * @param   hndl        Pointer to session handle
 * @param   dev         Device ID
 * @param   speed       Target speen in um/s
 * @param   storage_id  The destination memory location.
 *                      (1 = home, 2 = target, ...)
 * @param   mode        0 = one-by-one, 1 = move all axis simultanously.
 * @return  Negative value if an error occured. Zero or positive value otherwise
 */

LIBUMP_SHARED_EXPORT int ump_goto_mem_position_ext(ump_state *hndl, const int dev,
                                                   const int speed, const int storage_id,
                                                   const int mode);

/**
 * @brief An advanced API to stop manipulator by dev id.
 *
 * @param   hndl        Pointer to session handle
 * @param   dev         Device ID, SMCP1_ALL_MANIPULATORS to stop all.
 * @return  Negative value if an error occured. Zero or positive value otherwise
 */

LIBUMP_SHARED_EXPORT int ump_stop_ext(ump_state * hndl, const int dev);

/**
 * @brief Read socked to update the position and status caches
 *
 * This function can be used instead of a millisecond accurate delay
 * to read the socket and thus update the status and positions
 * into the cache
 *
 * @param   hndl       Pointer to session handle
 * @para    timelimit  delay in milliseconds
 * @return  Positive value indicates the count of received messages.
 *          Zero if no related messages was received. Negative value indicates an error.
 */

LIBUMP_SHARED_EXPORT int ump_receive(ump_state *hndl, const int timelimit);

/**
 * @brief An advanced API for reading positions of certain manipulator and
 *        allowing to control the position value timings.
 *
 * A zero time_limit (LIBUMP_TIMELIMIT_CACHE_ONLY) reads cached positions without
 * sending any request to the manipulator.
 * Value -1 (LIBUMP_TIMELIMIT_DISABLED) obtains the position always from the manipulator.
 *
 *
 * @param       hndl        Pointer to session handle
 * @param       dev         Device ID
 * @param       time_limit  Timelimit of cache values. If 0 then cached positions are used always.
 *                          If
 * @param[out]  x           Pointer to an allocated buffer for x-actuator position
 * @param[out]  y           Pointer to an allocated buffer for y-actuator position
 * @param[out]  z           Pointer to an allocated buffer for z-actuator position
 * @return  Negative value if an error occured. Zero or positive value otherwise
 */

LIBUMP_SHARED_EXPORT int ump_get_positions_ext(ump_state *hndl, const int dev, const int time_limit,
                                               int *x, int *y, int *z, int *w, int *elapsed);

/**
 * @brief An advanced API for reading actuator speeds of certain manipulator and
 *        obtaining time when the values were updated
 *
 *
 * @param       hndl        Pointer to session handle
 * @param       dev         Device ID
 *
 * @param[out]  x           Pointer to an allocated buffer for x-actuator speed
 * @param[out]  y           Pointer to an allocated buffer for y-actuator speed
 * @param[out]  z           Pointer to an allocated buffer for z-actuator speed
 * @param[out]  w           Pointer to an allocated buffer for w-actuator speed
 * @param[out]  elapsed     Pointer to an allocated buffer for value indicating position value age in ms
 * @return  Negative value if an error occured. Zero or positive value otherwise
 */

LIBUMP_SHARED_EXPORT  int ump_get_speeds_ext(ump_state *hndl, const int dev, float *x, float*y, float *z, float *w, int *elapsedptr);

/**
 * @brief An advanced API for reading positions of certain manipulator to the cache
 *
 * Value -1 (LIBUMP_TIMELIMIT_DISABLED) for the time_limit obtains the position always
 * from the manipulator.
 *
 *
 * @param       hndl        Pointer to session handle
 * @param       dev         Device ID
 * @param       time_limit  Timelimit of cache values. If 0 then cached positions are used always.
 *                          If
 * @return  Negative value if an error occured. Zero or positive value otherwise
 */

LIBUMP_SHARED_EXPORT int ump_read_positions_ext(ump_state *hndl, const int dev, const int time_limit);

/**
 * @brief An advanced API for obtaining single axis position value from the cache,
 * call after succeeded #ump_read_positions_ext
 *
 * @param       hndl        Pointer to session handle
 * @param       dev         Device ID
 * @param       axis        Axis name 'x','y','z' or 'w'
 * @return  axis position from the cache, 0 if value not available
 */

LIBUMP_SHARED_EXPORT int ump_get_position_ext(ump_state *hndl, const int dev, const char axis);

/**
 * @brief An advanced API for obtaining single axis speed from the cache,
 * works when manipulator is moving and updating the positions periodically
 *
 * @param       hndl        Pointer to session handle
 * @param       dev         Device ID
 * @param       axis        Axis name 'x','y','z' or 'w'
 * @return  axis movement speed in um/s
 */

LIBUMP_SHARED_EXPORT float ump_get_speed_ext(ump_state *hndl, const int dev, const char axis);





/**
 * @brief Take a step (relative movement from current position)
 *
 * @param   hndl    Pointer to session handle
 * @param   dev     Device ID
 * @param   step_x   step length (in nm) for X axis, negative value for backward, zero for axis not to be moved
 * @param   step_y   step length (in nm) for Y axis, negative value for backward, zero for axis not to be moved
 * @param   step_z   step length (in nm) for Z axis, negative value for backward, zero for axis not to be moved
 * @param   step_w   step length (in nm) for W axis, negative value for backward, zero for axis not to be moved
 * @param   speed_x  movement speed (in nm/ms or um/s) for X axis
 * @param   speed_y  movement speed (in nm/ms or um/s) for Y axis
 * @param   speed_z  movement speed (in nm/ms or um/s) for Z axis
 * @param   speed_w  movement speed (in nm/ms or um/s) for W axis
 * @return  Negative value if an error occured. Zero or positive value otherwise
 */

LIBUMP_SHARED_EXPORT int ump_take_step_ext(ump_state *hndl, const int dev,
                                           const int step_x, const int step_y, const int step_z, const int step_w,
                                           const int speed_x, const int speed_y, const int speed_z, const int speed_w);

/**
 * @brief ump_take_jackhammer_step_ext (moving manipulator with PEN mode max speed steps with 2 pulses
 * @param axis                  Target actuator: X == 0, Y == 1, Z == 2, W == 3
 * @param hndl                  Pointer to session handle
 * @param dev                   Device ID
 * @param iterations            Amount of iterations (loops) to execute 2 pulse sequence
 * @param pulse1_step_count     First pulse step count
 * @param pulse1_step_size      First pules step burst size - negative indicates backward movement
 * @param pulse2_step_count     Second pules step count
 * @param pulse2_step_size      Second uples step burst size - negative indicates backward movement
 * @return
 */
LIBUMP_SHARED_EXPORT int ump_take_jackhammer_step_ext(ump_state *hndl, const int dev,
                                                      const int axis,
                                                      const int iterations,
                                                      const int pulse1_step_count, const int pulse1_step_size,
                                                      int pulse2_step_count, const int pulse2_step_size);


/**
 * @brief ump_cmd_options
 * Set options for next cmd to be sent for manipulator.
 * This is one time set and will be reseted after sending the next message.
 * Can be used to set the trigger for next command (e.g. goto position)
 * @param   hndl        Pointer to session handle
 * @param   optionbits  Options bit to set. Use following:
 *  SMCP1_OPT_WAIT_TRIGGER_1 0x00000200 // Set message to be run when triggered by physical trigger line2
 *  SMCP1_OPT_PRIORITY       0x00000100 // Priorizes message to run first. // 0 = normal message
 *  SMCP1_OPT_REQ_BCAST      0x00000080 // send ACK, RESP or NOTIFY to the bcast address (combine with REQs below), 0 = unicast to the sender
 *  SMCP1_OPT_REQ_NOTIFY     0x00000040 //request notification (e.g. on completed memory drive), 0 = do not notify
 *  SMCP1_OPT_REQ_RESP       0x00000020 // request RESP, 0 = no RESP requested
 *  SMCP1_OPT_REQ_ACK        0x00000010 // request ACK, 0 = no ACK requested
 * @return  returns set flags
 */
LIBUMP_SHARED_EXPORT int ump_cmd_options(ump_state *hndl,int optionbits);

/**
 * @brief Send a command to manipulator.
 *
 * Note! This API is mainly for Sensapex internal development and production purpose.
 *
 * @param   hndl    Pointer to session handle
 * @param   dev     Device ID
 * @param   cmd     Command ID
 * @param   argc    Number of arguments (may be zero)
 * @param   argv    Pointer to command argument array (may be NULL)
 * @return  Negative value if an error occured. Zero or positive value otherwise
 */

LIBUMP_SHARED_EXPORT int ump_cmd(ump_state *hndl, const int dev, const int cmd,
                                 const int argc, const int *argv);

/**
 * @brief Send a command to manipulator and get response back.
 *
 * Note! This API is mainly for Sensapex internal development and production purpose.
 *
 * @param   hndl    Pointer to session handle
 * @param   dev     Device ID
 * @param   cmd     Command ID
 * @param   argc    Number of arguments (may be zero)
 * @param   argv    Pointer to command argument array (may be NULL)
 * @param   respsize Size of expected responses
 * @param   response Pointer to int array for response.
 * @return  Negative value if an error occured. Zero or positive value otherwise
 */
LIBUMP_SHARED_EXPORT int ump_cmd_ext(ump_state *hndl, const int dev, const int cmd,
                                     const int argc, const int *argv, int respsize, int *response);


/**
 * @brief Get a manipulator parameter value
 *
 * Note! This API is mainly for Sensapex internal development and production purpose.
 *
 * @param   hndl    Pointer to session handle
 * @param   dev     Device ID
 * @param   param_id Parameter id
 * @param[out] value Pointer to an allocated variable
 * @return  Negative value if an error occured. Zero or positive value otherwise
 */

LIBUMP_SHARED_EXPORT int ump_get_param(ump_state *hndl, const int dev, const int param_id, int *value);

/**
 * @brief Set a manipulator parameter value
 *
 * Note! This API is mainly for Sensapex internal development and production purpose and
 * should not be used unless you really know what you are doing.
 *
 * WARNING: Abusing this function may void device warranty
 *
 * @param   hndl      Pointer to session handle
 * @param   dev       Device ID
 * @param   param_id  Paramter id
 * @param   value     Data to be written
 * @return  Negative value if an error occured. Zero or positive value otherwise
 */

LIBUMP_SHARED_EXPORT int ump_set_param(ump_state *hndl, const int dev,
                                       const int param_id, const int value);
/**
 * @brief Get state of a manipulator feature
 *
 * @param   hndl    Pointer to session handle
 * @param   dev     Device ID
 * @param   feature_id Feature id
 * @return  Negative value if an error occured. 0 if feature disabled, 1 if enabled
 */

LIBUMP_SHARED_EXPORT int ump_get_feature(ump_state *hndl, const int dev, const int feature_id);

/**
 * @brief Enable or disable a manipulator feature (e.g. virtual X axis with )
 *
 * @param   hndl      Pointer to session handle
 * @param   dev       Device ID
 * @param   feature_id  Feature id
 * @param   value     0 to disable and 1 to enable feature
 * @return  Negative value if an error occured. Zero or positive value otherwise
 */

LIBUMP_SHARED_EXPORT int ump_set_feature(ump_state *hndl, const int dev,
                                         const int feature_id, const int value);


/**
 * @brief TCU remote control, select manipulator
 *
 * @param   hndl      Pointer to session handle
 * @param   dev       Manipulator device ID to be selected
 * @return  Negative value if an error occured. Zero or positive value otherwise
 */

LIBUMP_SHARED_EXPORT int ump_cu_select_manipulator(ump_state *hndl, const int dev);

/**
 * @brief TCU remote control, set speed mode
 *
 * @param   hndl      Pointer to session handle
 * @param   speed_mode Speed mode e.g. #LIBUMP_CU_SPEED_MODE_1
 * @param   pen_step_size Step size, affects only #speed_mode #LIBUMP_CU_SPEED_MODE_PEN
 * @return  Negative value if an error occured. Zero or positive value otherwise
 */

LIBUMP_SHARED_EXPORT int ump_cu_set_speed_mode(ump_state *hndl, const int speed_mode, const int pen_step_size);

/**
 * @brief TCU remote control, set active/inactive mode
 *
 * @param   hndl      Pointer to session handle
 * @param   active    0 to set TCU into inactive mode where TCU will not move manipulators,
 *                    1 back to normal
 * @return  Negative value if an error occured. Zero or positive value otherwise
 */

LIBUMP_SHARED_EXPORT int ump_cu_set_active(ump_state *hndl, const int active);

/**
 * @brief TCU remote control, get GUI application version number
 *
 * @param   hndl      Pointer to session handle
 * @param[out]  version Pointer to an allocated buffer for version numbers
 * @param       size    size of the above buffer (number of integers)
 *
 * This function should be called in this way
 * int version_buffer[5];
 * int ret = ump_cu_read_version(handle, buffer, 5);
 *
 * @return  Negative value if an error occured. Zero or positive value otherwise
 */

LIBUMP_SHARED_EXPORT int ump_cu_read_version(ump_state *hndl, int *version, const int size);

/**
 * @brief Get manipulators which are broadcasting inside the network
 * @param   hndl      Pointer to session handle
 * @param[out] devs   Pointer to list of devices found
 * @param[out] count  Count of devices seen
 * @return `true` if operation was successful, `false` otherwise
 */
LIBUMP_SHARED_EXPORT int ump_get_broadcasters(ump_state *hndl,int *devs,  int *count);


/**
 * @brief Clear SDK internal list of manipulators which are broadcasting inside the network. List will be populated automatically after a while.
 * @return `true` if operation was successful, `false` otherwise
 */
LIBUMP_SHARED_EXPORT int ump_clear_broadcasters(ump_state *hndl);

/*
 * End of the C-API
 */

#ifdef __cplusplus
} // end of extern "C"


#define LIBUMP_USE_LAST_DEV  0     /**< Use the selected device ID */

/*!
 * @class LibUmp
 * @brief A inline C++ wrapper class for a publis Sensapex uMp SDK
 * not depending on Qt or std classes
*/

class LibUmp
{
public:
    /**
     * @brief Constructor
     */
    LibUmp() {  _handle = NULL; }
    /**
     * @brief Destructor
     */
    virtual ~LibUmp()
    {   if(_handle) ump_close(_handle); }

    /**
     * @brief Open socket and initialize class state to communicate with manipulators
     * @param broadcastAddress  UDP target address as a string with traditional IPv4 syntax e.g. "169.254.255.255"
     * @param timeout           UDP message timeout in milliseconds
     * @return `true` if operation was successful, `false` otherwise
     */
    bool open(const char *broadcastAddress = LIBUMP_DEF_BCAST_ADDRESS, const unsigned int timeout = LIBUMP_DEF_TIMEOUT, const int group = LIBUMP_DEF_GROUP)
    {	return (_handle = ump_open(broadcastAddress, timeout, group)) != NULL; }

    /**
     * @brief Check if socket is open for manipulator communication
     * @return `true` if this instance of `LibUmp` holds an open UDP socket.
     */
    bool isOpen()
    { 	return _handle != NULL; }

    /**
     * @brief Close the socket (if open) and free the state structure allocated in open
     */
    void close()
    {	ump_close(_handle); _handle = NULL; }

    /**
     * @brief SDK library version
     * @return Pointer to version string
     */
    static const char *version()
    {   return ump_get_version(); }

    /**
     * @brief Select a manipulator
     * @param dev   Device ID
     * @return `true` if operation was successful, `false` otherwise
     */
    bool select(const int dev = LIBUMP_USE_LAST_DEV)
    {
        int retval = ump_select_dev(_handle, getDev(dev));
        ump_cu_select_manipulator(_handle, getDev(dev));
        return retval;
    }


    /**
     * @brief Check if a manipulator is available for communication
     * @param dev   Device ID
     * @return `true` if operation was successful, `false` otherwise
     */
    bool ping(const int dev = LIBUMP_USE_LAST_DEV)
    {	return  ump_ping(_handle, getDev(dev)) >= 0; }

    /**
     * @brief Get the status of manipulator
     * @param dev   Device ID
     * @return Manipulator status. See #ump_status for bit definitions
     */
    ump_status status(const int dev = LIBUMP_USE_LAST_DEV)
    { 	return	ump_get_status_ext(_handle, getDev(dev)); }

    /**
     * @brief Check if a status is an error status
     * @param status    Value to be checked
     * @return `true` is `status` is an error status.
     */
    static bool errorStatus(ump_status status)
    {	return	(int)status < 0; }

    /**
     * @brief Check if a status is a busy status
     * @param status    Value to be checked
     * @return `true` if `status` is a busy status.
     */
    static bool busyStatus(ump_status status)
    {	return	ump_is_busy_status(status) > 0; }

    /**
     * @brief Check if manipulator is busy
     * @param dev   Device ID
     * @return `true` if manipulator is busy, `false` otherwise
     */
    bool busy(const int dev = LIBUMP_USE_LAST_DEV)
    {   return ump_is_busy_ext(_handle, getDev(dev)) > 0; }

    /**
     * @brief Obtain memory or position drive status
     * @param   dev     Device ID
     * @return  Status of the selected manipulator, #LIBUMP_POS_DRIVE_COMPLETED,
     *          #LIBUMP_POS_DRIVE_BUSY or #LIBUMP_POS_DRIVE_FAILED
     */

    int driveStatus(const int dev = LIBUMP_USE_LAST_DEV)
    {   return ump_get_drive_status_ext(_handle, getDev(dev)); }

    /**
     * @brief Execute a manipulator command
     * @param cmd   Command ID
     * @param argc  number of command arguments
     * @param argv  array of command arguments (of argc size)
     * @param dev   Device ID
     * @return `true` if operation was successful, `false` otherwise
     */
    bool cmd(const unsigned char cmd, const int argc = 0,
             const int *argv = NULL,  const int dev = LIBUMP_USE_LAST_DEV)
    {	return	ump_cmd(_handle, getDev(dev), cmd, argc, argv) >= 0; }

    /**
     * @brief cmdOptions
     * Set options for next cmd to be sent for manipulator.
     * This is one time set and will be reseted after sending the next message.
     * Can be used to set the trigger for next command (e.g. goto position)
     * @param   hndl        Pointer to session handle
     * @param   optionbits  Options bit to set. Use following:
     *  SMCP1_OPT_WAIT_TRIGGER_1 0x00000200 // Set message to be run when triggered by physical trigger line2
     *  SMCP1_OPT_PRIORITY       0x00000100 // Priorizes message to run first. // 0 = normal message
     *  SMCP1_OPT_REQ_BCAST      0x00000080 // send ACK, RESP or NOTIFY to the bcast address (combine with REQs below), 0 = unicast to the sender
     *  SMCP1_OPT_REQ_NOTIFY     0x00000040 //request notification (e.g. on completed memory drive), 0 = do not notify
     *  SMCP1_OPT_REQ_RESP       0x00000020 // request RESP, 0 = no RESP requested
     *  SMCP1_OPT_REQ_ACK        0x00000010 // request ACK, 0 = no ACK requested
     * @return  returns set flags
     */
    int cmdOptions(const int flags)
    {  return ump_cmd_options(_handle, flags); }

    /**
     * @brief Execute a manipulator command with requiring response

     * @param cmd   Command ID
     * @param argc  number of command arguments
     * @param argv  array of command arguments (of argc size)
     * @param dev   Device ID
     * @param resp  Pointer to int array for response.
     * @param size  Response msg size
     * @return amount of data received, zero if none.
     */
    int cmd_resp(int *resp, int rsize,const int cmd, const int argc = 0,
                 const int *argv = NULL,  const int dev = LIBUMP_USE_LAST_DEV)
    {
        return ump_cmd_ext(_handle, getDev(dev), cmd, argc, argv, rsize, resp);
    }

    /**
     * @brief Read manipulator parameter
     * @param paramId    Parameter id
     * @param[out] value parameter value
     * @param dev        Device ID
     * @return `true` if operation was successful, `false` otherwise
     */
    bool getParam(const int paramId, int *value, const int dev = LIBUMP_USE_LAST_DEV)
    {	return  ump_get_param(_handle, getDev(dev), paramId, value) >= 0; }

    /**
     * @brief Set manipulator parameter value
     * @param paramId   Parameter id
     * @param value     Data to be written
     * @param dev       Device ID
     * @return `true` if operation was successful, `false` otherwise
     */
    bool setParam(const int paramId, const short value, const int dev = LIBUMP_USE_LAST_DEV)
    {	return  ump_set_param(_handle, getDev(dev), paramId, value) >= 0; }

    /**
     * @brief Get manipulator feature state
     * @param featureId  feature id
     * @param[out] value value
     * @param dev        Device ID
     *
     * @return `true` if operation was successful, `false` otherwise
     */
    bool getFeature(const int featureId, bool *value, const int dev = LIBUMP_USE_LAST_DEV)
    {
        int ret;
        if((ret = ump_get_feature(_handle, getDev(dev), featureId)) < 0)
            return false;
        *value = ret > 0;
        return true;
    }

    /**
     * @brief Enable or disable manipulator feature
     * @param featureId  feature id
     * @param state      enable or disable
     * @param dev        Device ID
     * @return `true` if operation was successful, `false` otherwise
     */
    bool setFeature(const int featureId, const bool state, const int dev = LIBUMP_USE_LAST_DEV)
    {	return  ump_set_feature(_handle, getDev(dev), featureId, state) >= 0; }

    /**
     * @brief TSC remote control, select manipulator
     * @param dev        manipulator dev id
     * @return `true` if operation was successful, `false` otherwise
     */
    bool tscSelectManipulator(const int dev)
    {	return  ump_cu_select_manipulator(_handle, dev) >= 0; }

    /**
     * @brief TSC remote control, select speed mode
     * @param speed_mode  TCU speed mode selection, e.g. #LIBUMP_CU_SPEED_MODE_2
     * @param pen_mode_step Step size, ignored for other speed modes
     * @return `true` if operation was successful, `false` otherwise
     */
    bool tscSetSpeed(const int speed_mode, const int pen_mode_step)
    {	return  ump_cu_set_speed_mode(_handle, speed_mode, pen_mode_step) >= 0; }

    /**
     * @brief TSC remote control, set active
     * @param active false to set TCU into inactive mode, true back to normal mode
     * @return `true` if operation was successful, `false` otherwise
     */
    bool tscSetActive(const bool active)
    {	return  ump_cu_set_active(_handle, active) >= 0; }


    /**
     * @brief Obtain the position of actuators.
     * @param x     Pointer to x-actuator position (may be NULL)
     * @param y     Pointer to y-actuator position (may be NULL)
     * @param z     Pointer to z-actuator position (may be NULL)
     * @param w     Pointer to w-actuator position (may be NULL)
     * @param dev   Device ID
     * @param       timeLimit  Timelimit of cache values. If `timeLimit` is 0 then
     * cached positions are used always. If `timeLimit` is #LIBUMP_TIMELIMIT_DISABLED
     * then positions are read from manipulator always.
     * @return `true` if operation was successful, `false` otherwise
     */
    bool getPositions(int *x, int *y, int *z, int *w,
                      const int dev = LIBUMP_USE_LAST_DEV,
                      const unsigned int timeLimit = LIBUMP_DEF_REFRESH_TIME)
    {   return ump_get_positions_ext(_handle, getDev(dev), timeLimit, x, y, z, w, NULL) >= 0; }

    /**
     * @brief Store the current position
     * @param dev       Device ID
     * @param storageId The destination memory location
     *        (0 = default, 1 = home, 2 = target, ... )
     * @return `true` if operation was successful, `false` otherwise
     */
    bool storeMem(const int dev = LIBUMP_USE_LAST_DEV, const int storageId = 0)
    {   return ump_store_mem_current_position_ext(_handle, getDev(dev), storageId) >= 0; }

    /**
     * @brief Move actuators to a stored position
     * @param dev           Device ID
     * @param storageId     The destination memory location.
     *                      (1 = home, 2 = target, ...)
     * @param speed         Movement speed (mode 1-5 or um/s)
     * @param allAxisSimultanously Drive mode (default one-by-one)
     * @return `true` if operation was successful, `false` otherwise
     */
    bool gotoMem(const int dev = LIBUMP_USE_LAST_DEV, const int storageId = 1,
                 const int speed = 0, const bool allAxisSimultanously = false)
    {   return ump_goto_mem_position_ext(_handle, getDev(dev), speed, storageId, allAxisSimultanously) >= 0; }

    /**
     * @brief Move actuators to given position
     * @param x      Destination position for x-actuator, use #LIBUMP_ARG_UNDEF for axis not to be moved
     * @param y      Destination position for y-actuator
     * @param z      Destination position for z-actuator
     * @param w      Destination position for w-actuator
     * @param speed  Movement speed mode (0 to use default value)
     * @param dev    Device ID (#LIBUMP_USE_LAST_DEV to use selected one)
     * @param allAxisSimultanously Drive mode (default one-by-one)
     * @return `true` if operation was successful, `false` otherwise
     */
    bool gotoPos(const int x, const int y, const int z, const int w,
                 const int speed,  const int dev = LIBUMP_USE_LAST_DEV,
                 const bool allAxisSimultanously = false)
    {   return ump_goto_position_ext(_handle, getDev(dev), x, y, z, w, speed, allAxisSimultanously) >= 0; }

    /**
     * @brief Move virtual axis position
     * @param x     Position to drive nm
     * @param speed Speed um/sec
     * @param dev   Device ID (#LIBUMP_USE_LAST_DEV to use selected one)
     * @return `true` if operation was successful, `false` otherwise
     */
    bool gotoVirtualPos(const int x, const int speed, const int dev = LIBUMP_USE_LAST_DEV) {
        return ump_goto_virtual_axis_position_ext(_handle,getDev(dev),x,speed);
    }
    /**
     * @brief Stop manipulator
     * @param dev   Device ID
     * @return `true` if operation was successful, `false` otherwise
     */
    bool stop(const int dev = LIBUMP_USE_LAST_DEV)
    {   return ump_stop_ext(_handle, getDev(dev)) >= 0; }

    /**
     * @brief Stop all manipulator
     * @return `true` if operation was successful, `false` otherwise
     */
    bool stopAll()
    {   return ump_stop_all(_handle) >= 0; }

     /**
     * @brief Get the latest error code from manipulator
     * @return #ump_error error code
     */
    ump_error lastError()
    {	return ump_last_error(_handle); }

    /**
     * @brief Get the latest error description from manipulator
     * @return Pointer to error description
     */
    const char *lastErrorText()
    { 	return ump_last_errorstr(_handle); }

    /**
     * @brief Get the manipulator firmware version
     * @param[out] version  Pointer to an allocated buffer for firmware version numbers
     * @param      size     Size of the above buffer (number of integers)
     * @param      dev      Device ID
     * @return `true` if operation was successful, `false` otherwise
     */
    bool readVersion(int *version, const int size, const int dev = LIBUMP_USE_LAST_DEV)
    {   return ump_read_version_ext(_handle, getDev(dev), version, size) >= 0; }

    /**
     * @brief TCU remote control, get GUI application version number
     *
     * @param[out]  version Pointer to an allocated buffer for version numbers. Buffer size needs to be >= 9!
     * @param       size    size of the above buffer (number of integers)
     *
     * @return  `true` if operation was successful, `false` otherwise
     */

    bool readTSCversion( char *version_str) {
        int version[5], ret = -1;

        ump_receive(_handle, 400);
        ret = ump_cu_read_version(_handle,version,5);

       if ( ret >= 0 ) {
           if ( version[0] < 5) {
               version_str[0] = version[0];
               version_str[1] = '.';
               version_str[2] = version[1];
               version_str[3] = '.';
               version_str[4] = version[2];
               version_str[5] = '.';
               version_str[6] = version[3];
               version_str[7] = '.';
               version_str[8] = version[4];
           }
        }

        return ret >= 0 ? true : false;
    }

    /**
     * @brief Get manipulators which are broadcasting inside the network
     * @param[out] devs   Pointer to list of devices found
     * @param[out] count  Count of devices seen
     * @return `true` if operation was successful, `false` otherwise
     */
    bool getBroadcasters(int *devs, int *count)
    {  return ump_get_broadcasters(_handle,devs,count); }


    /**
      * @brief Get manipulators which are broadcasting inside the network
      * @param[out] devs   Pointer to list of devices found
      * @param[out] count  Count of devices seen
      * @return `true` if operation was successful, `false` otherwise
      */
    bool clearBroadcastersList()
    {  return ump_clear_broadcasters(_handle); }

    /**
     * @brief Get the manipulator axis count
     * @param      dev      Device ID
     * @return  Negative value if an error occured. Axis count otherwise
     */
    int getAxisCount(const int dev = LIBUMP_USE_LAST_DEV)
    {   return ump_get_axis_count(_handle, getDev(dev)); }

    /**
     * @brief getAxisAngle
     * @param dev Device id
     * @param axis  x=0,y=1,z=2,w=3
     * @param layer x-layer = 0, y-layer = 1, z-layer = 2
     * @return Integer value of asked axis angle
     */
    int getAxisAngle(const int dev, const int axis, const int layer){
        return ump_cmd_get_axis_angle(_handle, dev, axis, layer);
    }


    /**
     * @brief Take a step (relative movement from current position)
     * @param   x,y,z,w  step length (in nm), negative value for backward, zero for axis not to be moved
     * @param   speed    movement speed (TODO: in nm/ms or um/s) for all axis, zero to use default value
     * @param   dev      Device ID
     * @return `true` if operation was successful, `false` otherwise
     */
    bool takeStep(const int x, const int y = 0, const int z = 0,
                  const int w = 0, const int speed = 0, const int dev = LIBUMP_USE_LAST_DEV)

    {   return ump_take_step_ext(_handle, getDev(dev), x, y, z, w, speed, speed, speed, speed); }

    /**
     * @brief Take a step (relative movement from current position) with separate speed for every axis
     * @param   step_x   step length (in nm) for X axis negative value for backward, zero for axis not to be moved
     * @param   step_y   step length (in nm) for Y axis negative value for backward, zero for axis not to be moved
     * @param   step_z   step length (in nm) for Z axis negative value for backward, zero for axis not to be moved
     * @param   step_w   step length (in nm) for W axis negative value for backward, zero for axis not to be moved
     * @param   speed_x  movement speed in nm/ms or um/s for X axis, zero to use default value
     * @param   speed_y  movement speed in nm/ms or um/s for Y axis, zero to use default value
     * @param   speed_z  movement speed in nm/ms or um/s for Z axis, zero to use default value
     * @param   speed_w  movement speed in nm/ms or um/s for W axis, zero to use default value
     * @param   dev      Device ID
     * @return `true` if operation was successful, `false` otherwise
     */
    bool takeStep(const int step_x, const int step_y, const int step_z, const int step_w,
                  const int speed_x, const int speed_y, const int speed_z,
                  const int speed_w, const int dev = LIBUMP_USE_LAST_DEV)
    {   return ump_take_step_ext(_handle, getDev(dev), step_x, step_y, step_z, step_w,
                                 speed_x, speed_y, speed_z, speed_w); }


    bool takeJackHammerStep( const int axis, const int iterations, const int pulse1_step_count, const int pulse1_step_size, int pulse2_step_count, const int pulse2_step_size, const int dev = LIBUMP_USE_LAST_DEV )
    {
       return ump_take_jackhammer_step_ext(_handle, getDev(dev), axis, iterations, pulse1_step_count, pulse1_step_size, pulse2_step_count, pulse2_step_size );
    }

    /**
     * @brief Get C-API handle
     * @return pointer to #ump_state handle
     */
    ump_state *getHandle()
    {   return _handle; }

    /**
     * @brief Check that the manipulator's unicast address is known
     * @param   dev   Device ID
     * @return `true` if manipulator's unicast address is known, `false` otherwise
     */
    bool hasUnicastAddress(const int dev = LIBUMP_USE_LAST_DEV)
    {
        int dev_index;
        if(!_handle)
            return false;
        if(dev == LIBUMP_USE_LAST_DEV)
            dev_index = _handle->last_device_sent;
        else
            dev_index = dev;
        return dev_index >= 0 && dev_index < LIBUMP_MAX_MANIPULATORS &&
                _handle->addresses[dev_index].sin_addr.s_addr != 0;
    }

    /**
     * @brief Set up external log print functio by default the library writes
     *        to the stderr if verbose level is higher than zero.
     *
     * @param   hndl            Pointer to session handle
     * @param   verbose_level   Verbose level (zero to disable, higher value for more detailed printouts)
     * @param   func            Pointer to the custom log print function.
     *                          May be NULL if setting only verbose level for internal log print out to stderr
     * @param   arg             Pointer argument to be looped to the above function may be e.g. a typecasted
     *                          file handle, optional, may be NULL
     * @return  Negative value if an error occured. Zero or positive value otherwise
     */
    bool set_log_callback(const int verbose_level,ump_log_print_func func, const void *arg) {
        return ump_set_log_func(_handle, verbose_level, func, arg);
    }


    /**
     * @brief Process incoming messages (may update status or location cache)
     * @return number of messages received
     */
    int recv(const int timelimit)
    {   return ump_receive(_handle, timelimit); }

private:
    /**
     * @brief Resolves device ID, #LIBUMP_USE_LAST_DEV handled in a special way
     * @param  dev    Device ID
     * @return Device ID
     */
    int getDev(const int dev)
    {
        if(dev == LIBUMP_USE_LAST_DEV && _handle)
            return _handle->last_device_sent;
        return dev;
    }
    /**
     * @brief Session handle
     */
    ump_state *_handle;
};

#endif // C++

#endif // LIBUMP_H
