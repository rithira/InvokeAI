import { createSelector } from '@reduxjs/toolkit';
import _ from 'lodash';
import { useHotkeys } from 'react-hotkeys-hook';
import { activeTabNameSelector } from 'features/options/optionsSelectors';
import {
  setShouldShowBoundingBox,
  setTool,
  toggleShouldLockBoundingBox,
} from 'features/canvas/store/canvasSlice';
import { useAppDispatch, useAppSelector } from 'app/store';
import { useRef } from 'react';
import { canvasSelector } from 'features/canvas/store/canvasSelectors';
import { CanvasTool } from '../store/canvasTypes';
import { getCanvasStage } from '../util/konvaInstanceProvider';

const selector = createSelector(
  [canvasSelector, activeTabNameSelector],
  (canvas, activeTabName) => {
    const {
      cursorPosition,
      shouldLockBoundingBox,
      shouldShowBoundingBox,
      tool,
    } = canvas;

    return {
      activeTabName,
      isCursorOnCanvas: Boolean(cursorPosition),
      shouldLockBoundingBox,
      shouldShowBoundingBox,
      tool,
    };
  },
  {
    memoizeOptions: {
      resultEqualityCheck: _.isEqual,
    },
  }
);

const useInpaintingCanvasHotkeys = () => {
  const dispatch = useAppDispatch();
  const { activeTabName, shouldShowBoundingBox, tool } =
    useAppSelector(selector);

  const previousToolRef = useRef<CanvasTool | null>(null);

  const canvasStage = getCanvasStage();

  //  Toggle lock bounding box
  useHotkeys(
    'shift+w',
    () => {
      dispatch(toggleShouldLockBoundingBox());
    },
    {
      preventDefault: true,
    },
    [activeTabName]
  );

  useHotkeys(
    'shift+h',
    () => {
      dispatch(setShouldShowBoundingBox(!shouldShowBoundingBox));
    },
    {
      preventDefault: true,
    },
    [activeTabName, shouldShowBoundingBox]
  );

  useHotkeys(
    ['space'],
    (e: KeyboardEvent) => {
      if (e.repeat) return;

      canvasStage?.container().focus();

      if (tool !== 'move') {
        previousToolRef.current = tool;
        dispatch(setTool('move'));
      }

      if (
        tool === 'move' &&
        previousToolRef.current &&
        previousToolRef.current !== 'move'
      ) {
        dispatch(setTool(previousToolRef.current));
        previousToolRef.current = 'move';
      }
    },
    {
      keyup: true,
      keydown: true,
      preventDefault: true,
    },
    [tool, previousToolRef]
  );
};

export default useInpaintingCanvasHotkeys;